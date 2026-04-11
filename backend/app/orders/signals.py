from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='orders.Order')
def award_delivery_bonus(sender, instance, created, **kwargs):
    if created:
        return
    if instance.status != instance.Status.DELIVERED:
        return

    from .models import BonusTransaction

    # Don't double-credit
    if BonusTransaction.objects.filter(
        order=instance,
        transaction_type=BonusTransaction.Type.EARNED,
    ).exists():
        return

    total = sum(
        item.dish_variant.price * item.quantity
        for item in instance.items.select_related('dish_variant').all()
    )
    bonus = (Decimal(str(total)) - instance.bonus_discount) * Decimal('0.05')
    if bonus <= 0:
        return

    BonusTransaction.objects.create(
        user=instance.user,
        order=instance,
        amount=bonus.quantize(Decimal('0.01')),
        transaction_type=BonusTransaction.Type.EARNED,
    )
