"""Fetch (or generate) a thumbnail image for every product.

Usage:
    python manage.py fetch_product_images
    python manage.py fetch_product_images --force
    python manage.py fetch_product_images --source generate

By default it tries to download a labelled placeholder from a public service
and, if there is no network, generates an equivalent card locally with Pillow.
Either way the image is stored under MEDIA_ROOT/products/ and linked to the
product, so the demo works fully offline afterwards.
"""

from __future__ import annotations

import io
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image, ImageDraw, ImageFont

from apps.catalog.models import Product

logger = logging.getLogger(__name__)

WIDTH, HEIGHT = 600, 400
CATEGORY_COLORS = {
    "laptop": (47, 107, 255),
    "phone": (15, 157, 118),
    "tv": (124, 58, 237),
    "accessory": (224, 123, 57),
}
CATEGORY_LABELS = {
    "laptop": "Portátil",
    "phone": "Celular",
    "tv": "Televisor",
    "accessory": "Accesorio",
}
DOWNLOAD_TIMEOUT = 8


class Command(BaseCommand):
    help = "Download or generate a thumbnail image for each product."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite images that already exist.",
        )
        parser.add_argument(
            "--source",
            choices=["auto", "download", "generate"],
            default="auto",
            help="Where to get images from (default: auto = download then generate).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        force = options["force"]
        source = options["source"]
        products = Product.objects.all().order_by("sku")
        created = downloaded = generated = skipped = 0

        for product in products:
            if product.image and not force:
                skipped += 1
                continue

            data = None
            if source in {"auto", "download"}:
                data = self._download(product)
                if data:
                    downloaded += 1
            if data is None and source in {"auto", "generate"}:
                data = self._generate(product)
                generated += 1
            if data is None:
                self.stderr.write(f"No se pudo obtener imagen para {product.sku}")
                continue

            filename = f"{product.sku.lower()}.png"
            if product.image:
                product.image.delete(save=False)
            product.image.save(filename, ContentFile(data), save=True)
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imágenes listas: {created} asignadas "
                f"({downloaded} descargadas, {generated} generadas, "
                f"{skipped} omitidas)."
            )
        )

    def _download(self, product: Product) -> bytes | None:
        text = urllib.parse.quote_plus(f"{product.brand} {product.name}")
        color = CATEGORY_COLORS.get(product.category, (27, 36, 48))
        hex_color = "%02x%02x%02x" % color
        url = f"https://placehold.co/{WIDTH}x{HEIGHT}/{hex_color}/ffffff/png?text={text}"
        request = urllib.request.Request(url, headers={"User-Agent": "EmtelcoSeed/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.info("Download failed for %s: %s", product.sku, exc)
            return None

    def _generate(self, product: Product) -> bytes:
        color = CATEGORY_COLORS.get(product.category, (27, 36, 48))
        image = Image.new("RGB", (WIDTH, HEIGHT), color)
        draw = ImageDraw.Draw(image)

        brand_font = self._font(26)
        name_font = self._font(40)
        meta_font = self._font(24)

        draw.text((40, 44), product.brand.upper(), font=brand_font, fill=(255, 255, 255, 200))

        y = 100
        for line in self._wrap(product.name, name_font, WIDTH - 80):
            draw.text((40, y), line, font=name_font, fill=(255, 255, 255))
            y += 48

        label = CATEGORY_LABELS.get(product.category, "")
        draw.text((40, HEIGHT - 80), label, font=meta_font, fill=(255, 255, 255))
        price = f"${int(product.price):,} COP".replace(",", ".")
        text_width = draw.textlength(price, font=meta_font)
        draw.text((WIDTH - 40 - text_width, HEIGHT - 80), price, font=meta_font, fill=(255, 255, 255))

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    @staticmethod
    def _font(size: int):
        try:
            return ImageFont.load_default(size=size)
        except TypeError:  # very old Pillow
            return ImageFont.load_default()

    def _wrap(self, text: str, font, max_width: int) -> list[str]:
        words = text.split()
        lines: list[str] = []
        current = ""
        probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        for word in words:
            candidate = f"{current} {word}".strip()
            if probe.textlength(candidate, font=font) <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines[:3]
