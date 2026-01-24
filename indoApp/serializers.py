from rest_framework import serializers
from indoApp.models import *


class CategorySerializer(serializers.ModelSerializer):
    category_type = serializers.SerializerMethodField()
    full_path = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "parent",
            "is_active",
            "category_type",
            "full_path",
        ]

    def get_category_type(self, obj):
        if obj.parent is None:
            return "MAIN"
        if obj.children.exists():
            return "SUB"
        return "LEAF"  # sub name

    def get_full_path(self, obj):
        path = []
        node = obj
        while node:
            path.append(node.name)
            node = node.parent
        return " > ".join(reversed(path))




class BrandBrochureSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = BrandBrochure
        fields = ["id", "category", "category_name", "title", "brochure_file", "is_active"]


class BrandSerializer(serializers.ModelSerializer):
    brochures = BrandBrochureSerializer(many=True, read_only=True)

    class Meta:
        model = Brand
        fields = ["id", "name", "logo", "is_active", "brochures"]



class AttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attribute
        fields = ["id", "name", "data_type", "unit"]




class CategoryAttributeSerializer(serializers.ModelSerializer):
    attribute = AttributeSerializer(read_only=True)
    attribute_id = serializers.PrimaryKeyRelatedField(
        source="attribute",
        queryset=Attribute.objects.all(),
        write_only=True
    )

    class Meta:
        model = CategoryAttribute
        fields = [
            "id",
            "category",
            "attribute",
            "attribute_id",
            "is_required",
            "sort_order",
        ]





class ProductAttributeValueSerializer(serializers.ModelSerializer):
    attribute = AttributeSerializer(read_only=True)

    value = serializers.SerializerMethodField()

    class Meta:
        model = ProductAttributeValue
        fields = [
            "id",
            "attribute",
            "value",
            "value_text",
            "value_number",
            "value_bool",
        ]

    def get_value(self, obj):
        # ✅ One clean "value" output for frontend
        if obj.value_text not in [None, ""]:
            return obj.value_text
        if obj.value_number is not None:
            return obj.value_number
        if obj.value_bool is not None:
            return obj.value_bool
        return None





class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)

    category_id = serializers.PrimaryKeyRelatedField(
        source="category",
        queryset=Category.objects.all(),
        write_only=True
    )
    brand_id = serializers.PrimaryKeyRelatedField(
        source="brand",
        queryset=Brand.objects.all(),
        write_only=True,
        allow_null=True,
        required=False
    )

    attributes = ProductAttributeValueSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "price",
            "old_price",
            "stock",
            "is_active",
            "created_at",
            "min_order_quantity",
            "is_exclusive",
            "is_featured",
            "rating",
            "image",
            "category",
            "brand",

            "category_id",
            "brand_id",

            "attributes",
        ]


class HomeBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeBanner
        fields = ["id", "banner_type", "image", "title", "description", "is_active"]