from django.db import models


class Country(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("inactive", "Inactive"),
    )

    SERVER_CHOICES = (
        ("server1", "Server 1"),
        ("server2", "Server 2"),
        ("server3", "Server 3"),
    )

    provider_id = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    name = models.CharField(
        max_length=100,
        unique=False
    )

    iso_code = models.CharField(
        max_length=10,
        unique=False,  # Changed from True to False
        blank=True,
        null=True
    )

    phone_code = models.CharField(
        max_length=10,
        blank=True,
        null=True
    )

    flag = models.ImageField(
        upload_to="flags/",
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="active",
    )

    server = models.CharField(
        max_length=20,
        choices=SERVER_CHOICES,
        default="server3",
    )

    display_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "Country"
        verbose_name_plural = "Countries"
        unique_together = [["name", "server"], ["iso_code", "server"]]  # Both name and iso_code unique per server

    def __str__(self):
        return f"{self.name} ({self.server})"