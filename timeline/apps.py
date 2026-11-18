from django.apps import AppConfig


class TimelineConfig(AppConfig):
    name = 'timeline'

    def ready(self):
        from timeline import signals  # noqa: F401
