from rest_framework import viewsets, filters, permissions
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from rest_framework.permissions import AllowAny
from rest_framework import generics


from indoApp.models import (
    Category,
    Brand,
    Product,
    Attribute,
    CategoryAttribute,
    ProductAttributeValue,
    BrandBrochure,
    HomeBanner,
)

from indoApp.serializers import (
    CategorySerializer,
    BrandSerializer,
    ProductSerializer,
    AttributeSerializer,
    CategoryAttributeSerializer,
    ProductAttributeValueSerializer,
    BrandBrochureSerializer,
    HomeBannerSerializer,
)


# ============================
# CATEGORY VIEWSET
# ============================
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().select_related("parent")
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active", "parent"]
    search_fields = ["name", "slug"]
    ordering_fields = ["name", "id"]
    ordering = ["name"]


# ============================
# BRAND VIEWSET
# ============================
class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [permissions.AllowAny]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["name"]
    ordering_fields = ["name", "id"]
    ordering = ["name"]


# ============================
# BRAND BROCHURE CREATE VIEW
# ============================
class BrandBrochureCreateView(generics.CreateAPIView):
    queryset = BrandBrochure.objects.all()
    serializer_class = BrandBrochureSerializer


# ============================
# ATTRIBUTE VIEWSET
# ============================
class AttributeViewSet(viewsets.ModelViewSet):
    queryset = Attribute.objects.all()
    serializer_class = AttributeSerializer
    permission_classes = [permissions.AllowAny]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["data_type"]
    search_fields = ["name"]
    ordering_fields = ["name", "id"]
    ordering = ["name"]


# ============================
# CATEGORY ATTRIBUTE VIEWSET
# (Which attributes belong to which category)
# ============================
class CategoryAttributeViewSet(viewsets.ModelViewSet):
    queryset = CategoryAttribute.objects.select_related("category", "attribute").all()
    serializer_class = CategoryAttributeSerializer
    permission_classes = [permissions.AllowAny]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "attribute", "is_required"]
    search_fields = ["category__name", "attribute__name"]
    ordering_fields = ["sort_order", "id"]
    ordering = ["sort_order"]


# ============================
# PRODUCT ATTRIBUTE VALUE VIEWSET
# (Values for a product’s attributes)
# ============================
class ProductAttributeValueViewSet(viewsets.ModelViewSet):
    queryset = ProductAttributeValue.objects.select_related("product", "attribute").all()
    serializer_class = ProductAttributeValueSerializer
    permission_classes = [permissions.AllowAny]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["product", "attribute"]
    search_fields = ["product__name", "attribute__name"]
    ordering_fields = ["id"]
    ordering = ["id"]


# ============================
# PRODUCT VIEWSET
# ============================
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active", "category", "brand"]
    search_fields = ["name", "slug", "category__name", "brand__name"]
    ordering_fields = ["created_at", "price", "stock", "id"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """
        ✅ Optimized queryset (important for production)
        - select_related: category, brand
        - prefetch_related: attributes + attribute details
        """
        return (
            Product.objects.select_related("category", "brand")
            .prefetch_related(
                Prefetch(
                    "attributes",
                    queryset=ProductAttributeValue.objects.select_related("attribute").all(),
                )
            )
            .all()
        )



class SearchAPIView(APIView):
    """
    Premium Search API for:
    - products
    - brands
    - categories (MAIN/SUB/LEAF)

    Returns suggestions grouped for dropdown UI.
    MAIN/SUB categories include "leaf_slugs" so frontend can redirect to leaf-based filter pages.
    """

    permission_classes = [AllowAny]

    def get_leaf_descendants(self, category: Category):
        """
        Return all leaf categories under a category (including itself if it is leaf).
        This works even if user searches MAIN or SUB.
        """
        # ✅ If already LEAF
        if category.category_type == "LEAF":
            return Category.objects.filter(id=category.id, is_active=True)

        # ✅ Otherwise: collect leaf descendants
        # This assumes you have parent relation as self FK
        # (parent -> children reverse relation)
        return Category.objects.filter(
            is_active=True,
            category_type="LEAF",
            full_path__startswith=category.name  # fallback idea (optional)
        )

    def get(self, request):
        q = request.GET.get("q", "").strip()

        if not q:
            return Response(
                {
                    "query": "",
                    "products": [],
                    "brands": [],
                    "categories": {
                        "main": [],
                        "sub": [],
                        "leaf": [],
                    },
                },
                status=status.HTTP_200_OK,
            )

        # ✅ Limits for dropdown suggestions (keep it fast)
        products_limit = int(request.GET.get("products_limit", 8))
        categories_limit = int(request.GET.get("categories_limit", 6))
        brands_limit = int(request.GET.get("brands_limit", 6))

        # ==========================================================
        # ✅ PRODUCTS SEARCH
        # ==========================================================
        product_qs = (
            Product.objects.select_related("category", "brand")
            .filter(is_active=True)
            .filter(
                Q(name__icontains=q)
                | Q(slug__icontains=q)
                | Q(category__name__icontains=q)
                | Q(category__full_path__icontains=q)
                | Q(brand__name__icontains=q)
            )
            .order_by("-created_at")[:products_limit]
        )

        products = []
        for p in product_qs:
            products.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "slug": p.slug,
                    "image": request.build_absolute_uri(p.image.url)
                    if getattr(p, "image", None)
                    else None,
                    "price": str(p.price),
                    "old_price": str(p.old_price) if p.old_price else None,
                    "brand": {
                        "id": p.brand.id,
                        "name": p.brand.name,
                        "logo": request.build_absolute_uri(p.brand.logo.url)
                        if getattr(p.brand, "logo", None)
                        else None,
                    }
                    if p.brand
                    else None,
                    "leaf_category": {
                        "id": p.category.id,
                        "name": p.category.name,
                        "slug": p.category.slug,
                        "full_path": getattr(p.category, "full_path", None),
                    }
                    if p.category
                    else None,
                }
            )

        # ==========================================================
        # ✅ BRANDS SEARCH
        # ==========================================================
        brand_qs = (
            Brand.objects.filter(is_active=True)
            .filter(Q(name__icontains=q))
            .order_by("name")[:brands_limit]
        )

        brands = []
        for b in brand_qs:
            brands.append(
                {
                    "id": b.id,
                    "name": b.name,
                    "logo": request.build_absolute_uri(b.logo.url)
                    if getattr(b, "logo", None)
                    else None,
                }
            )

        # ==========================================================
        # ✅ CATEGORIES SEARCH (MAIN / SUB / LEAF)
        # ==========================================================
        category_qs = (
            Category.objects.filter(is_active=True)
            .filter(Q(name__icontains=q) | Q(slug__icontains=q) | Q(full_path__icontains=q))
            .order_by("parent_id", "name")[: categories_limit * 2]
        )

        main_categories = []
        sub_categories = []
        leaf_categories = []

        for c in category_qs:
            item = {
                "id": c.id,
                "name": c.name,
                "slug": c.slug,
                "category_type": c.category_type,
                "full_path": getattr(c, "full_path", None),
            }

            # ✅ If MAIN or SUB → return leaf slugs for redirection
            if c.category_type in ["MAIN", "SUB"]:
                leafs = Category.objects.filter(
                    is_active=True,
                    category_type="LEAF",
                    full_path__startswith=c.name  # optional fallback
                )

                # ✅ BEST WAY: get descendants properly (recommended)
                # If your category model has children relation, use recursion OR adjacency query
                # Here we handle it in a simple safe way:
                leaf_slugs = list(
                    Category.objects.filter(
                        is_active=True,
                        category_type="LEAF",
                        full_path__icontains=c.name,
                    )
                    .values_list("slug", flat=True)
                    .distinct()[:12]
                )

                item["leaf_slugs"] = leaf_slugs

            # ✅ Put into correct group
            if c.category_type == "MAIN":
                main_categories.append(item)
            elif c.category_type == "SUB":
                sub_categories.append(item)
            else:
                leaf_categories.append(item)

        # keep dropdown small
        main_categories = main_categories[:categories_limit]
        sub_categories = sub_categories[:categories_limit]
        leaf_categories = leaf_categories[:categories_limit]

        return Response(
            {
                "query": q,
                "products": products,
                "brands": brands,
                "categories": {
                    "main": main_categories,
                    "sub": sub_categories,
                    "leaf": leaf_categories,
                },
            },
            status=status.HTTP_200_OK,
        )


class HomeBannerViewSet(viewsets.ModelViewSet):
    queryset = HomeBanner.objects.all()
    serializer_class = HomeBannerSerializer


class LatestLaunchesViewSet(viewsets.ModelViewSet):
    queryset = LatestLaunches.objects.all()
    serializer_class = LatestLaunchesSerializer
