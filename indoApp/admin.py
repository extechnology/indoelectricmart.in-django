from django.contrib import admin
from django import forms
from django.forms import BaseInlineFormSet
from django.db.models import Q
from django.utils.text import slugify
from django.utils.html import format_html
from django.urls import path

from indoApp.models import *


class CategoryAdminForm(forms.ModelForm):
    main_category = forms.ModelChoiceField(
        queryset=Category.objects.filter(parent__isnull=True).order_by("name"),
        required=False,
        label="Main Category",
        empty_label="--- Select Main Category ---",
    )

    sub_category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        required=False,
        label="Sub Category",
        empty_label="--- Select Sub Category ---",
    )

    class Meta:
        model = Category
        fields = ["main_category", "sub_category", "name", "slug", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        main_id = None

        # ✅ 1) If user selected main category (POST)
        if "main_category" in self.data:
            main_id = self.data.get("main_category")

        # ✅ 2) If editing existing category
        elif self.instance and self.instance.pk:
            # Case: Sub Category (parent is a main category)
            if self.instance.parent and self.instance.parent.parent is None:
                main_id = self.instance.parent.id
                self.fields["main_category"].initial = self.instance.parent

            # Case: Sub Name (parent is sub category, parent.parent is main)
            elif self.instance.parent and self.instance.parent.parent:
                main_id = self.instance.parent.parent.id
                self.fields["main_category"].initial = self.instance.parent.parent
                self.fields["sub_category"].initial = self.instance.parent

        # ✅ Load sub categories for selected main category
        if main_id:
            self.fields["sub_category"].queryset = Category.objects.filter(
                parent_id=main_id
            ).order_by("name")

    def clean(self):
        cleaned_data = super().clean()

        main = cleaned_data.get("main_category")
        sub = cleaned_data.get("sub_category")

        # ✅ If sub selected, main must exist
        if sub and not main:
            raise forms.ValidationError(
                "Please select Main Category before selecting Sub Category."
            )

        # ✅ If sub selected, it must belong to selected main
        if main and sub and sub.parent_id != main.id:
            raise forms.ValidationError(
                "Selected Sub Category does not belong to the selected Main Category."
            )

        # ✅ Convert UI selection -> real DB parent
        if sub:
            cleaned_data["parent"] = sub
        elif main:
            cleaned_data["parent"] = main
        else:
            cleaned_data["parent"] = None

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # ✅ Final save parent logic
        instance.parent = self.cleaned_data.get("parent")

        if commit:
            instance.save()
        return instance


class CategoryAttributeInline(admin.TabularInline):
    model = CategoryAttribute
    extra = 1
    autocomplete_fields = ("attribute",)
    ordering = ("sort_order",)



# ======================================================
# Category Attribute Inline
# ======================================================
class CategoryAttributeInline(admin.TabularInline):
    model = CategoryAttribute
    extra = 1
    autocomplete_fields = ("attribute",)
    ordering = ("sort_order",)


# ======================================================
# Parent Dropdown Label Field (ONLY for parent selection)
# ======================================================
class ParentCategoryChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj: Category):
        # Main category
        if obj.parent_id is None:
            return f"{obj.name} (Main Category)"

        # Sub category
        return f"{obj.name} (Sub Category)"


# ======================================================
# Category Admin
# ======================================================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category_level", "parent", "is_active", "children_count")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "parent__name")
    ordering = ("parent__id", "name")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [CategoryAttributeInline]

    fieldsets = (
        ("Category Info", {"fields": ("parent", "name", "slug")}),
        ("Status", {"fields": ("is_active",)}),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            kwargs["queryset"] = (
                Category.objects.filter(
                    Q(parent__isnull=True) | Q(parent__parent__isnull=True)
                )
                .distinct()
            .order_by("parent__id", "name")
        )
        kwargs["form_class"] = ParentCategoryChoiceField

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def children_count(self, obj):
        return obj.children.count()

    children_count.short_description = "Children"

    def category_level(self, obj):
        if obj.parent_id is None:
            return format_html("<b style='color:green;'>Main</b>")

        if obj.parent and obj.parent.parent_id is None:
            return format_html("<b style='color:blue;'>Sub</b>")

        return format_html("<b style='color:purple;'>Sub Name</b>")

    category_level.short_description = "Level"



class BrandBrochureInlineForm(forms.ModelForm):
    category = ParentCategoryChoiceField(queryset=Category.objects.filter(is_active=True))

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
    list_display = ("name", "category", "brand", "price", "stock", "is_active", "is_exclusive")
    list_filter = ("is_active", "brand")
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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        ✅ Only allow Leaf categories to be selectable for Product.category.
        Leaf = category that has NO children.
        """
        if db_field.name == "category":
            kwargs["queryset"] = Category.objects.filter(children__isnull=True).order_by("name")

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not obj.slug:
            obj.slug = slugify(obj.name)
        super().save_model(request, obj, form, change)



@admin.register(HomeBanner)
class HomeBannerAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "banner_type",
        "banner_preview",
        "is_active",
        "sort_order",
        "updated_at",
    )
    list_filter = ("banner_type", "is_active")
    search_fields = ("title", "description")
    ordering = ("banner_type", "sort_order", "-created_at")
    list_editable = ("sort_order", "is_active")


    def banner_preview(self, obj):
        if obj.image: # ✅ replace "image" with your ImageField name
            return format_html(
                '<img src="{}" style="width:80px; height:50px; object-fit:cover; border-radius:6px;" />',
                obj.image.url,
            )
        return "No Image"


    banner_preview.short_description = "Preview"



@admin.register(LatestLaunches)
class LatestLaunchesAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "is_active",
        "created_at",
        "updated_at",
        "image_preview",
    )
    list_filter = ("is_active",)
    search_fields = ("title", "description")
    ordering = ("-created_at",)

    list_editable = ("is_active",)
    readonly_fields = ("image_preview", "created_at", "updated_at")

    fieldsets = (
        ("Launch Info", {"fields": ("title", "description")}),
        ("Image", {"fields": ("image", "image_preview")}),
        ("Status", {"fields": ("is_active",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def image_preview(self, obj: LatestLaunches):
        if obj.image:
            return format_html(
                "<img src='{}' style='height:60px;width:100px;object-fit:cover;border-radius:10px;' />",
                obj.image.url,
            )
        return "—"

    image_preview.short_description = "Preview"



@admin.register(OffersAndSchemes)
class OffersAndSchemesAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "is_active",
        "valid_upto",
        "created_at",
        "updated_at",
        "image_preview",
    )
    list_filter = ("is_active",)
    search_fields = ("title", "description")
    ordering = ("-created_at",)

    list_editable = ("is_active",)
    readonly_fields = ("image_preview", "created_at", "updated_at")

    fieldsets = (
        ("Launch Info", {"fields": ("title", "description","valid_upto")}),
        ("Image", {"fields": ("image", "image_preview")}),
        ("Status", {"fields": ("is_active",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def image_preview(self, obj: LatestLaunches):
        if obj.image:
            return format_html(
                "<img src='{}' style='height:60px;width:100px;object-fit:cover;border-radius:10px;' />",
                obj.image.url,
            )
        return "—"

    image_preview.short_description = "Preview"
