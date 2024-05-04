import os
import signal
import subprocess
import sys
from pathlib import Path
from unittest import mock

from django_mongodb.client import DatabaseClient

from django.db import connection
from django.test import SimpleTestCase


class MongoDBDbshellCommandTestCase(SimpleTestCase):
    def settings_to_cmd_args_env(self, settings_dict, parameters=None):
        if parameters is None:
            parameters = []
        return DatabaseClient.settings_to_cmd_args_env(settings_dict, parameters)

    def test_fails_with_keyerror_on_incomplete_config(self):
        with self.assertRaises(KeyError):
            self.settings_to_cmd_args_env({})

    def test_basic_params_specified_in_settings(self):
        for options_parameters in [(None, None, None), ("value1", "value2", True)]:
            with self.subTest(keys=options_parameters):
                authentication_database, authentication_mechanism, retry_writes = (
                    options_parameters
                )
                if authentication_database is not None:
                    expected_args = [
                        "mongosh",
                        "--username",
                        "someuser",
                        "--password",
                        "somepassword",
                        "--authenticationDatabase",
                        "value1",
                        "--authenticationMechanism",
                        "value2",
                        "--retryWrites",
                        "true",
                        "mongodb://somehost:444/somedbname",
                    ]
                else:
                    expected_args = [
                        "mongosh",
                        "--username",
                        "someuser",
                        "--password",
                        "somepassword",
                        "mongodb://somehost:444/somedbname",
                    ]

                self.assertEqual(
                    self.settings_to_cmd_args_env(
                        {
                            "NAME": "somedbname",
                            "USER": "someuser",
                            "PASSWORD": "somepassword",
                            "HOST": "somehost",
                            "PORT": 444,
                            "OPTIONS": {
                                "authenticationDatabase": authentication_database,
                                "authenticationMechanism": authentication_mechanism,
                                "retryWrites": retry_writes,
                            },
                        }
                    ),
                    (expected_args, None),
                )

    def test_options_override_settings_proper_values(self):
        settings_port = 444
        options_port = 555
        self.assertNotEqual(settings_port, options_port, "test pre-req")
        expected_args = ["mongosh", "mongodb://user:pass@host:port/db"]
        expected_env = None
        self.assertEqual(
            self.settings_to_cmd_args_env(
                {
                    "NAME": "settingdbname",
                    "USER": "settinguser",
                    "PASSWORD": "settingpassword",
                    "HOST": "settinghost",
                    "PORT": settings_port,
                    "OPTIONS": {"uri": "mongodb://user:pass@host:port/db"},
                }
            ),
            (expected_args, expected_env),
        )

    def test_connect_with_fileconfigs(self):
        expected_args = [
            "mongosh",
            "--username",
            "someuser",
            "--password",
            "someuser",
            "mongodb://host:3333/somedbname",
            "path_to_file1",
            "path_to_file2",
        ]
        expected_env = None
        self.assertEqual(
            self.settings_to_cmd_args_env(
                {
                    "NAME": "somedbname",
                    "USER": "someuser",
                    "PASSWORD": "somepassword",
                    "HOST": "host",
                    "PORT": "3333",
                    "OPTIONS": {"filenames": ["path_to_file1", "path_to_file2"]},
                }
            ),
            (expected_args, expected_env),
        )

    def test_empty_host_parameter(self):
        for port in [(None,), ("4444",)]:
            with self.subTest(keys=port):
                self.assertEqual(
                    self.settings_to_cmd_args_env(
                        {
                            "NAME": "somedbname",
                            "USER": None,
                            "PASSWORD": None,
                            "HOST": None,
                            "PORT": port,
                            "OPTIONS": {},
                        },
                        ["--help"],
                    ),
                    (["mongosh", "--help"], None),
                )

    def test_crash_password_does_not_leak(self):
        # The password doesn't leak in an exception that results from a client
        # crash.
        self.skipTest("We are unable to pass the password via environment vairable")
        args, env = DatabaseClient.settings_to_cmd_args_env(
            {
                "NAME": "somedbname",
                "USER": "someuser",
                "PASSWORD": "somepassword",
                "HOST": "somehost",
                "PORT": 444,
                "OPTIONS": {},
            },
            [],
        )
        if env:
            env = {**os.environ, **env}
        fake_client = Path(__file__).with_name("fake_client.py")
        args[0:1] = [sys.executable, str(fake_client)]
        with self.assertRaises(subprocess.CalledProcessError) as ctx:
            subprocess.run(args, check=True, env=env)

        self.assertNotIn("somepassword", str(ctx.exception))

    def test_sigint_handler(self):
        """SIGINT is ignored in Python and passed to Mongodb to abort queries."""

        def _mock_subprocess_run(*args, **kwargs):
            handler = signal.getsignal(signal.SIGINT)
            self.assertEqual(handler, signal.SIG_IGN)

        sigint_handler = signal.getsignal(signal.SIGINT)
        # The default handler isn't SIG_IGN.
        self.assertNotEqual(sigint_handler, signal.SIG_IGN)
        with mock.patch("subprocess.run", new=_mock_subprocess_run):
            connection.client.runshell([])
        # dbshell restores the original handler.
        self.assertEqual(sigint_handler, signal.getsignal(signal.SIGINT))
