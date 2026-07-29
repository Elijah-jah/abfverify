from django.db import models


class Service(models.Model):
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
        unique=True,
        null=True,
        blank=True,
        help_text="Provider Service ID (for InstantNums numeric IDs)"
    )

    code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Provider service code (e.g., am, fb, ig for DaisySMS)"
    )

    name = models.CharField(
        max_length=255,
        unique=False  # Changed from True to False
    )

    icon = models.ImageField(
        upload_to="service_icons/",
        blank=True,
        null=True
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="active"
    )

    server = models.CharField(
        max_length=20,
        choices=SERVER_CHOICES,
        default="server3",
    )

    display_order = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "Service"
        verbose_name_plural = "Services"
        unique_together = [["name", "server"]]  # Added: same name allowed on different servers

    def __str__(self):
        return f"{self.name} ({self.server})"