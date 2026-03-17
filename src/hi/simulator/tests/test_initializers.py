from django.test import TestCase

from hi.simulator.initializers import SimulatorInitializer
from hi.simulator.models import SimProfile
from hi.simulator.simulator_manager import SimulatorManager


class SimulatorInitializerTestCase(TestCase):

    def test_run_creates_default_profile(self):
        initializer = SimulatorInitializer()

        initializer.run()

        self.assertEqual(SimProfile.objects.count(), 1)
        self.assertTrue(
            SimProfile.objects.filter(name=SimulatorManager.DEFAULT_PROFILE_NAME).exists()
        )

    def test_run_is_idempotent(self):
        initializer = SimulatorInitializer()

        initializer.run()
        initializer.run()

        self.assertEqual(SimProfile.objects.count(), 1)
