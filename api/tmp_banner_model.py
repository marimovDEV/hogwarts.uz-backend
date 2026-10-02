
class Banner(models.Model):
    """Homepage Hero Banner Slider"""
    title = models.CharField(max_length=200)
    subtitle = models.TextField(blank=True)
    image = models.ImageField(upload_to='banners/')
    mobile_image = models.ImageField(upload_to='banners/', blank=True, null=True)
    button_text = models.CharField(max_length=50, blank=True)
    button_link = models.CharField(max_length=200, blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'banners'
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title
