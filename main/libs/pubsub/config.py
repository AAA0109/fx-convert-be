from typing import Optional, Dict

import google.auth
from google.oauth2 import service_account

import main.libs.pubsub.middleware as middleware
import main.libs.pubsub.publisher as publisher
import main.settings.base as settings

DEFAULT_MIDDLEWARE = ["main.libs.pubsub.middleware.LoggingMiddleware"]

_topic_id = None


class Config:
    """
    Pub/Sub configuration base class which provides common configuration needed for all pub/sub implementations.

    The base config specifies the following settings:
        * 'TOPIC_ID'    : The topic ID to publish on.
        * 'MIDDLEWARE'  : A list of middleware classes to use. The default is `~main.pubsub.middleware.LoggingMiddleware`
    """

    def __init__(self, pubsub_settings: Dict[str, str]) -> None:
        """
        Constructor.
        :param pubsub_settings: Settings specific to pub/sub.
        """
        self.middleware = pubsub_settings.get("MIDDLEWARE", DEFAULT_MIDDLEWARE)
        self._topic_id = pubsub_settings.get('TOPIC_ID')


class GooglePubSubConfig(Config):
    """
    Google Cloud Pub/Sub specific configuration.

    Google Cloud configuration in local development mode requires the followig fields:
        * 'GC_PROJECT_ID': the Google Cloud Project ID
        * 'GC_CREDENTIAL_PATH': The path to the credential's file used to authenticate.

    In google cloud deployment we don't need to provide either.
    """

    def __init__(self, pubsub_settings: Dict[str, 'Any']) -> None:
        super(GooglePubSubConfig, self).__init__(pubsub_settings)
        self._gc_project_id = pubsub_settings.get('GC_PROJECT_ID', None)
        self._gc_credentials_path = pubsub_settings.get('GC_CREDENTIALS_PATH', None)
        self._credentials = None  # This will be initialized later.

    @property
    def credentials_path(self):
        return self._gc_credentials_path

    @property
    def google_credentials(self) -> 'google.auth.credentials.CorpaySettings':
        """
        Get the Google Cloud credentials provider.

        If a 'GC_CREDENTIALS_PATH' was provided then that file is used to instantiate the credentials, otherwise
        the default instantiation is used. The default configuration utilizes a number of different options:
            * GOOGLE_APPLICATION_CREDENTIALS environemntal variable
            * Google Cloud SDK is installed and configured with default application credentials
            * If the application is running in the `App Engine standard environment`

        :return: the google credential provider.
        :raise: `~google.auth.exceptions.DefaultCredentialsError` if the credentials cannot be instantiated.
        """
        if self.credentials_path:
            # Credentials were provided, this is most likely in local development
            self._credentials = service_account.Credentials.from_service_account_file(self.credentials_path)
        else:
            # This case should be in production where google provides the actual authentication.
            credentials, project_id = google.auth.default()
            self._credentials = credentials
            if not self._gc_project_id:
                self._gc_project_id = project_id
        return self._credentials

    @property
    def google_project_id(self) -> Optional[str]:
        """
        Get the Google Cloud project ID.

        If a 'GC_PROJECT_ID' is provided in the settings then it is used, otherwise the credential object's project
        ID is used. If no credentials and no project id

        :return: The project id if it is configured or None otherwise.
        """
        if self._gc_project_id:
            return self._gc_project_id
        elif self.credentials:
            return self.credentials.project_id
        else:
            return None

    @property
    def topic_id(self) -> str:
        return self._topic_id


def init(pubsub_settings: 'settings', **kwargs):
    """
    Initialize the pubsub module.

    Note that this method uses the presence of the TOPIC_ID setting to determine whether we should  instantiate a
    Google Cloud Pub/Sub or a mock one.
    Use this method if you intend to use global variables for pub/sub rather than dependency injection.

    :param pubsub_settings: The pubsub settings.
    :param kwargs: Any additional keyword arguments that should be passed to the middleware layer.
    """
    # TODO(Ghais) Use dynamic loading to instantiate this object by configuring a provider class in the settings.
    if pubsub_settings is None or pubsub_settings.get('TOPIC_ID', None):
        config = GooglePubSubConfig(pubsub_settings)
        publisher.init_google(config.google_project_id, config.google_credentials)
        publisher.set_default_topic_id(config.topic_id)
        middleware.register_middleware(config, **kwargs)
    else:
        config = Config(pubsub_settings)
        publisher.init_null(config)
