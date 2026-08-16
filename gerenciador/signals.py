from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .constants import ORGANIZATION_SLUG
from .models import Membership, Organization


# Vincula novas contas à organização padrão.
@receiver(post_save, sender=get_user_model())
def add_user_to_organization(sender, instance, created, **kwargs):
    if not created:
        return
    organization = Organization.objects.filter(slug=ORGANIZATION_SLUG).first()
    if organization:
        Membership.objects.get_or_create(
            organization=organization,
            user=instance,
            defaults={"is_active": instance.is_active},
        )
