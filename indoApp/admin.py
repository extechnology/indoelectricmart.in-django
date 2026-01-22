from django.contrib import admin
from django import forms
from django.forms import BaseInlineFormSet
from django.db.models import Q
from django.utils.text import slugify
from django.utils.html import format_html

from indoApp.models import (
    Category,
    Brand,
    Product,
    Attribute,
    CategoryAttribute,
    ProductAttributeValue,
    BrandBrochure,
)


# ======================================================
# CATEGORY ADMIN FORM (Parent dropdown clean)
# ======================================================
class CategoryAdminForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "parent" in self.fields:
            # ✅ allow only valid parents:
            # 1) root categories (main categories)
            # 2) sub categories (categories that already have children)
            # ❌ exclude leaf categories (sub names)
            self.fields["parent"].queryset = Category.objects.filter(
                Q(parent__isnull=True) | Q(children__isnull=False)
            ).distinct()

            # ✅ clearer parent labels
            self.fields["parent"].label_from_instance = self.parent_label

    def parent_label(self, obj: Category):
        if obj.parent is None:
            return f"{obj.name} (Main Category)"
        return f"{obj.name} (Sub Category)"


# ======================================================
# CATEGORY ATTRIBUTE INLINE (assign attributes to category)
# ======================================================
class CategoryAttributeInline(admin.TabularInline):
    model = CategoryAttribute
    extra = 1
    autocomplete_fields = ("attribute",)
    ordering = ("sort_order",)


# ======================================================
# CATEGORY ADMIN
# ======================================================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryAdminForm

    list_display = ("name", "category_level", "parent", "children_count", "is_active")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug", "parent__name")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("parent__name", "name")

    # ✅ Parent should come first
    fieldsets = (
        ("Hierarchy", {"fields": ("parent",)}),
        ("Category Info", {"fields": ("name", "slug")}),
        ("Status", {"fields": ("is_active",)}),
    )

    # ✅ Assign allowed attributes per Category directly here
    inlines = [CategoryAttributeInline]

    def children_count(self, obj):
        return obj.children.count()
    children_count.short_description = "Children"

    def category_level(self, obj):
        if obj.parent is None:
            return format_html("<b style='color:green;'>{}</b>", "Main Category")
        if obj.children.exists():
            return format_html("<b style='color:blue;'>{}</b>", "Sub Category")
        return format_html("<b style='color:purple;'>{}</b>", "Sub Name")
    category_level.short_description = "Type"




class CategoryChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj: Category):
        # Main category
        if obj.parent is None:
            return f"{obj.name} (Main Category)"

        # Leaf category (no children)
        if not obj.children.exists():
            return f"{obj.name} (Sub Name)"

        # Sub category (has parent + has children)
        return f"{obj.name} (Sub Category)"


class BrandBrochureInlineForm(forms.ModelForm):
    category = CategoryChoiceField(queryset=Category.objects.filter(is_active=True))

    class Meta:
        model = BrandBrochure
        fields = "__all__"


class BrandBrochureInline(admin.TabularInline):
    model = BrandBrochure
    form = BrandBrochureInlineForm
    extra = 1


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("name",)
    inlines = [BrandBrochureInline]


# ======================================================
# ATTRIBUTE ADMIN
# ======================================================
@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ("name", "data_type", "unit")
    list_filter = ("data_type",)
    search_fields = ("name",)
    ordering = ("name",)


# ======================================================
# PRODUCT ATTRIBUTE INLINE (Values per product)
# ======================================================
class UniqueAttributeInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen = set()

        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue

            attr = form.cleaned_data.get("attribute")
            if attr in seen:
                raise forms.ValidationError("Duplicate attribute detected for this product.")
            seen.add(attr)


class ProductAttributeValueInline(admin.TabularInline):
    model = ProductAttributeValue
    formset = UniqueAttributeInlineFormSet
    extra = 1
    autocomplete_fields = ("attribute",)
    fields = ("attribute", "value_text", "value_number", "value_bool")
    show_change_link = True


# ======================================================
# PRODUCT ADMIN FORM (only leaf categories shown)
# ======================================================
class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "category" in self.fields:
            self.fields["category"].queryset = Category.objects.filter(children__isnull=True)


# ======================================================
# PRODUCT ADMIN
# ======================================================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm

    list_display = ("name", "category", "brand", "price", "stock", "is_active","is_exclusive")
    list_filter = ("is_active", "category", "brand")
    search_fields = ("name", "slug", "category__name", "brand__name")
    ordering = ("-created_at",)

    autocomplete_fields = ("brand",)
    prepopulated_fields = {"slug": ("name",)}

    inlines = [ProductAttributeValueInline]

    fieldsets = (
        ("Basic Info", {"fields": ("name", "slug", "category", "brand", "min_order_quantity", "is_exclusive", "is_featured", "rating", "image")}),
        ("Pricing", {"fields": ("price", "old_price")}),
        ("Inventory", {"fields": ("stock", "is_active")}),
        ("Description", {"fields": ("description",)}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.slug:
            obj.slug = slugify(obj.name)
        super().save_model(request, obj, form, change)
