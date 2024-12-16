from main.apps.webhook.constants import WEBHOOK_EVENTS, WEBHOOK_EVENT_GROUPS


def sync_webhook_events(apps):
    Event = apps.get_model('webhook', 'Event')
    for event in WEBHOOK_EVENTS:
        Event.objects.get_or_create(
            type=event['type'],
            defaults={'name': event['name']}
        )


def sync_webhook_event_groups(apps):
    EventGroup = apps.get_model('webhook', 'EventGroup')
    Event = apps.get_model('webhook', 'Event')

    for group in WEBHOOK_EVENT_GROUPS:
        group_obj, created = EventGroup.objects.get_or_create(
            name=group['name'],
            defaults={'slug': group.get('slug', group['name'].lower())}
        )

        # Get all events for this group
        group_events = Event.objects.filter(type__in=group['events'])

        # Add new events to the group
        for event in group_events:
            group_obj.events.add(event)

        # Remove events that are no longer in the group
        group_obj.events.remove(*group_obj.events.exclude(type__in=group['events']))


def sync_webhooks(apps, schema_editor):
    sync_webhook_events(apps)
    sync_webhook_event_groups(apps)
