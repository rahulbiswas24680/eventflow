import io
from datetime import timedelta

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.images import ImageFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from events.models import Event, EventImage, TicketType
from user_profiles.models import Organizer, Role

User = get_user_model()

EVENTS_DATA = [
    {"name": "Summer Music Festival 2026", "category": "Music", "desc": "A massive outdoor music festival featuring top artists from around the world. Live bands, DJs, food stalls, and an unforgettable atmosphere under the stars.", "days_from_now": 60, "location": "Central Park, New York"},
    {"name": "Jazz & Blues Night", "category": "Music", "desc": "An intimate evening of smooth jazz and soulful blues. Featuring renowned musicians and a curated wine selection.", "days_from_now": 45, "location": "Blue Note, Mumbai"},
    {"name": "AI & Machine Learning Conference", "category": "Technology", "desc": "Deep dive into the latest AI advancements. Workshops on LLMs, computer vision, and practical ML deployment.", "days_from_now": 30, "location": "Convention Centre, Bangalore"},
    {"name": "Startup Pitch Fest", "category": "Business", "desc": "Watch 20 early-stage startups pitch to a panel of top VCs. Network with founders, investors, and industry experts.", "days_from_now": 20, "location": "WeWork, Delhi"},
    {"name": "Digital Marketing Masterclass", "category": "Business", "desc": "Learn SEO, social media strategy, and paid advertising from industry experts who've scaled brands to millions.", "days_from_now": -10, "location": "Online"},
    {"name": "Modern Web Development Bootcamp", "category": "Technology", "desc": "Three-day hands-on bootcamp covering React, Next.js, and Node.js. Build a full-stack app from scratch.", "days_from_now": 50, "location": "T-Hub, Hyderabad"},
    {"name": "Watercolor Painting Workshop", "category": "Arts", "desc": "A relaxing weekend workshop for all skill levels. Learn watercolor techniques and create your own masterpiece.", "days_from_now": 25, "location": "Art Gallery, Pune"},
    {"name": "Photography Exhibition: Urban Frames", "category": "Arts", "desc": "A curated exhibition showcasing stunning urban photography from emerging artists across India.", "days_from_now": -5, "location": "National Gallery, Delhi"},
    {"name": "IPL Finals Watch Party", "category": "Sports", "desc": "Cheer for your team on the big screen! Food, drinks, and high-energy crowd. Be there for the final showdown.", "days_from_now": 15, "location": "Sports Bar, Mumbai"},
    {"name": "Yoga & Wellness Retreat", "category": "Health", "desc": "Weekend retreat focusing on mindfulness, yoga, and holistic wellness. Recharge your mind and body.", "days_from_now": 40, "location": "Rishikesh, Uttarakhand"},
    {"name": "Gourmet Food Festival", "category": "Food", "desc": "Taste cuisines from 30+ top restaurants and street food vendors. Live cooking demos by celebrity chefs.", "days_from_now": 55, "location": "Jio World Garden, Mumbai"},
    {"name": "Wine & Cheese Tasting Evening", "category": "Food", "desc": "An elegant evening of wine tasting paired with artisanal cheeses. Guided by sommeliers.", "days_from_now": -2, "location": "Hotel Taj, Goa"},
    {"name": "Marathon for a Cause", "category": "Sports", "desc": "10K run supporting education for underprivileged children. Medals for all finishers, prizes for top runners.", "days_from_now": 35, "location": "Marine Drive, Mumbai"},
    {"name": "Entrepreneurship Summit", "category": "Business", "desc": "Two-day summit with talks from founders of unicorns. Topics: fundraising, scaling, and building culture.", "days_from_now": 70, "location": "HICC, Hyderabad"},
    {"name": "Classical Music Evening", "category": "Music", "desc": "An enchanting evening of Hindustani classical music featuring a renowned sitar maestro and tabla accompaniment.", "days_from_now": -15, "location": "Kamani Auditorium, Delhi"},
    {"name": "Data Science with Python Workshop", "category": "Technology", "desc": "Hands-on workshop covering pandas, numpy, scikit-learn, and building ML models with real-world datasets.", "days_from_now": 10, "location": "Online"},
    {"name": "Stand-Up Comedy Night", "category": "Arts", "desc": "A night of laughter with India's top stand-up comedians. 18+ only. Bring your friends!", "days_from_now": 5, "location": "The Habitat, Mumbai"},
    {"name": "Organic Farming Workshop", "category": "Food", "desc": "Learn sustainable farming practices, composting, and how to grow your own organic vegetables at home.", "days_from_now": -30, "location": "Organic Farm, Nashik"},
]


class Command(BaseCommand):
    help = "Seed sample events across various categories"

    def add_arguments(self, parser):
        parser.add_argument(
            '--with-images',
            action='store_true',
            help='Download placeholder images from picsum.photos (slower)',
        )

    def handle(self, *args, **options):
        self._bypass_redis()

        user = self._get_or_create_user()
        organizer = self._get_or_create_organizer(user)
        created = 0
        download_images = options['with_images']

        for data in EVENTS_DATA:
            if Event.objects.filter(name=data["name"]).exists():
                self.stdout.write(self.style.WARNING(f"Skipped (exists): {data['name']}"))
                continue

            event_date = timezone.now() + timedelta(days=data["days_from_now"])
            has_finished = data["days_from_now"] < -1

            event = Event.objects.create(
                organizer=organizer,
                name=data["name"],
                description=data["desc"],
                date=event_date,
                location=data["location"],
                metadata={"category": data["category"]},
                is_virtual="Online" in data["location"],
                is_published=True,
                is_active=True,
                has_finished_event=has_finished,
            )

            TicketType.objects.create(
                event=event, name="General Admission", price=499, quantity_available=200,
            )
            TicketType.objects.create(
                event=event, name="VIP Pass", price=1499, quantity_available=50,
            )

            if download_images:
                self._add_image(event, data["name"])

            created += 1
            self.stdout.write(self.style.SUCCESS(f"Created: {data['name']} [{data['category']}]"))

        self.stdout.write(self.style.SUCCESS(f"\nDone! {created} events created."))
        if not download_images:
            self.stdout.write(self.style.WARNING("Tip: Re-run with --with-images to download placeholder images."))

    def _bypass_redis(self):
        settings.CACHES["default"] = {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
        settings.CELERY_TASK_ALWAYS_EAGER = True

    def _get_or_create_user(self):
        user, _ = User.objects.get_or_create(
            email="demo@eventflow.com",
            defaults={"username": "demoorganizer", "is_active": True},
        )
        if not user.pk:
            user.set_unusable_password()
            user.save()
        role, _ = Role.objects.get_or_create(name="organizer")
        user.available_roles.add(role)
        user.current_role = role
        user.save()
        return user

    def _get_or_create_organizer(self, user):
        org, _ = Organizer.objects.get_or_create(
            user=user,
            defaults={
                "organizer_name": "EventFlow Demo",
                "organizer_email": "demo@eventflow.com",
                "organizer_phone": "+91XXXXXXXXXX",
                "is_active": True,
                "created_by": user,
                "modified_by": user,
            },
        )
        return org

    def _add_image(self, event, name):
        seed = abs(hash(name)) % 1000
        url = f"https://picsum.photos/seed/{seed}/800/600"
        try:
            resp = requests.get(url, timeout=10, allow_redirects=True)
            resp.raise_for_status()
            img_file = ImageFile(io.BytesIO(resp.content), name=f"{seed}.jpg")
            EventImage.objects.create(event=event, image=img_file)
            self.stdout.write(self.style.SUCCESS(f"  + image for {name}"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  No image for {name}: {e}"))
