from django.conf import settings
from django.db import migrations


def create_carmel_organization(apps, schema_editor):
    Organization = apps.get_model('gerenciador', 'Organization')
    Membership = apps.get_model('gerenciador', 'Membership')
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))
    organization, _ = Organization.objects.get_or_create(slug='carmel', defaults={'name': 'Carmel'})
    existing_user_ids = Membership.objects.filter(organization=organization).values_list('user_id', flat=True)
    Membership.objects.bulk_create([
        Membership(organization=organization, user=user, role='member')
        for user in User.objects.exclude(pk__in=existing_user_ids)
    ])


class Migration(migrations.Migration):
    dependencies = [('gerenciador', '0001_initial')]
    operations = [migrations.RunPython(create_carmel_organization, migrations.RunPython.noop)]
