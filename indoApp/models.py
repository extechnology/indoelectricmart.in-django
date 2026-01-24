from django.db import models
from django.utils.text import slugify

class Category(models.Model):

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True
    )
    

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Categories"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["parent"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=120, unique=True)
    logo = models.ImageField(upload_to="brands/", null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class BrandBrochure(models.Model):
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name="brochures"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="brand_brochures"
    )

    brochure_file = models.FileField(upload_to="brand_brochures/")
    title = models.CharField(max_length=200, blank=True, null=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("brand", "category")
        indexes = [
            models.Index(fields=["brand"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        return f"{self.brand.name} - {self.category.name}"



class Product(models.Model):
    category = models.ForeignKey(
        "Category",
        on_delete=models.PROTECT,
        related_name="products"
    )
    brand = models.ForeignKey(
        "Brand",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products"
    )
    

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=300, unique=True)
    image = models.ImageField(upload_to="products/", null=True, blank=True)
    rating = models.IntegerField(default=5)
    min_order_quantity = models.PositiveIntegerField(default=1)
    is_exclusive = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    old_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Attribute(models.Model):
    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "bool"
    CHOICE = "choice"

    DATA_TYPES = [
        (TEXT, "Text"),
        (NUMBER, "Number"),
        (BOOLEAN, "Boolean"),
        (CHOICE, "Choice"),
    ]

    name = models.CharField(max_length=100)
    data_type = models.CharField(max_length=20, choices=DATA_TYPES, default=TEXT)
    unit = models.CharField(max_length=20, blank=True)  # eg: mm, meter, inch

    def __str__(self):
        return self.name


class CategoryAttribute(models.Model):
    category = models.ForeignKey("Category", on_delete=models.CASCADE, related_name="category_attributes")
    attribute = models.ForeignKey("Attribute", on_delete=models.CASCADE)

    is_required = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("category", "attribute")

    def __str__(self):
        return f"{self.category.name} - {self.attribute.name}"


class ProductAttributeValue(models.Model):
    product = models.ForeignKey("Product", on_delete=models.CASCADE, related_name="attributes")
    attribute = models.ForeignKey("Attribute", on_delete=models.CASCADE)

    value_text = models.CharField(max_length=255, null=True, blank=True)
    value_number = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    value_bool = models.BooleanField(null=True, blank=True)

    class Meta:
        unique_together = ("product", "attribute")

    def __str__(self):
        return f"{self.product.name} - {self.attribute.name}"





class HomeBanner(models.Model):
    class BannerType(models.TextChoices):
        HERO_CAROUSEL = "HERO", "Hero Carousel"
        EXCLUSIVE = "EXCLUSIVE", "Exclusive Banner"
        TOP_BRANDS = "TOP_BRANDS", "Top Brands Banner"
        OFFERS = "OFFERS", "Offers Banner"

    banner_type = models.CharField(
        max_length=20,
        choices=BannerType.choices,
        db_index=True,
    )

    image = models.ImageField(upload_to="home_banners/")
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    sort_order = models.PositiveIntegerField(default=0)  # ✅ important
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("banner_type", "sort_order", "-created_at")
        indexes = [
            models.Index(fields=["banner_type", "is_active"]),
        ]

    def __str__(self):
        return f"{self.get_banner_type_display()} - {self.title}"



class LatestLaunches(models.Model):
    image = models.ImageField(upload_to="latest_launches/")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.title}"