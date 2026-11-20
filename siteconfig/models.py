from django.core.cache import cache
from django.db import models

CACHE_KEY = "siteconfig:site_settings"


class SiteSettings(models.Model):
    """Singleton row holding site-wide branding (logo etc.)."""

    logo = models.ImageField(upload_to="site/", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return "Site Settings"

    def save(self, *args, **kwargs):
        # Enforce singleton: always update row pk=1.
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(CACHE_KEY)

    def delete(self, *args, **kwargs):
        cache.delete(CACHE_KEY)
        return super().delete(*args, **kwargs)

    @classmethod
    def load(cls):
        """Return the singleton settings, cached to avoid a DB hit per request.

        Falls back to an empty (unsaved) instance when the table is not
        migrated yet or the database is unavailable, so pages keep working
        with the static default logo.
        """
        obj = cache.get(CACHE_KEY)
        if obj is None:
            try:
                obj, _created = cls.objects.get_or_create(pk=1)
            except Exception:
                obj = cls()
            else:
                cache.set(CACHE_KEY, obj, 60 * 60)
        return obj
