import unittest

from eventsourcing.domain.model.events import assert_event_handlers_empty
from eventsourcing.domain.model.example import Example, register_new_example
from eventsourcing.domain.model.snapshot import take_snapshot
from eventsourcing.infrastructure.event_player import EventPlayer
from eventsourcing.infrastructure.event_store import EventStore
from eventsourcing.infrastructure.persistence_subscriber import PersistenceSubscriber
from eventsourcing.infrastructure.stored_events.python_objects_stored_events import PythonObjectsStoredEventRepository


class TestEventPlayer(unittest.TestCase):

    def setUp(self):
        assert_event_handlers_empty()
        self.ps = None

    def tearDown(self):
        if self.ps is not None:
            self.ps.close()
        assert_event_handlers_empty()

    def test_get_entity(self):
        # Setup an event store, using Python objects.
        event_store = EventStore(stored_event_repo=PythonObjectsStoredEventRepository())

        # Store example events.
        event1 = Example.Created(entity_id='entity1', timestamp=3, a=1, b=2)
        event_store.append(event1)
        event2 = Example.Created(entity_id='entity2', timestamp=4, a=2, b=4)
        event_store.append(event2)
        event3 = Example.Created(entity_id='entity3', timestamp=5, a=3, b=6)
        event_store.append(event3)
        event4 = Example.Discarded(entity_id='entity3', timestamp=6, entity_version=1)
        event_store.append(event4)

        # Check the event sourced entities are correct.
        # - just use a trivial mutator that always instantiates the 'Example'.
        event_player = EventPlayer(event_store=event_store, mutator=Example.mutator, domain_class_name='Example')

        # The the reconstituted entity has correct attribute values.
        self.assertEqual('entity1', event_player['entity1'].id)
        self.assertEqual(1, event_player['entity1'].a)
        self.assertEqual(2, event_player['entity2'].a)

        # Check entity3 raises KeyError.
        self.assertRaises(KeyError, event_player.__getitem__, 'entity3')

    def test_snapshots(self):
        stored_event_repo = PythonObjectsStoredEventRepository()
        event_store = EventStore(stored_event_repo)
        self.ps = PersistenceSubscriber(event_store)
        event_player = EventPlayer(event_store=event_store, mutator=Example.mutator, domain_class_name='Example')

        # Create a new entity.
        registered_example = register_new_example(a=123, b=234)

        # Take a snapshot.
        take_snapshot(registered_example)

        # Check the event sourced entities are correct.
        #  - should use a snapshot with no additional events
        retrieved_example = event_player[registered_example.id]
        self.assertEqual(retrieved_example.a, registered_example.a)

        # Change attribute value.
        retrieved_example.a = 999
        retrieved_example.a = 9999

        # Check the event sourced entities are correct.
        #  - should use a snapshot with two additional events
        retrieved_example = event_player[registered_example.id]
        self.assertEqual(retrieved_example.a, 9999)

        # Take a snapshot.
        take_snapshot(retrieved_example)

        # Check the event sourced entities are correct.
        #  - should use a snapshot with two additional events
        retrieved_example = event_player[registered_example.id]
        self.assertEqual(retrieved_example.a, 9999)

