from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from core.models import Course, EnrollmentRequest, News, youtube_id


class EnrollmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.course = Course.objects.create(direction="frontend", slug="web", title_ru="Frontend")

    def test_valid_request_is_saved(self):
        response = self.client.post(reverse("core:enroll"), {
            "name": "Гульнара", "phone": "+996 700 112 233", "email": "g@mail.kg", "age": 11,
            "course": self.course.pk, "message": "Хотим на пробный урок", "next": "/",
        })
        self.assertRedirects(response, reverse("core:enroll_success"), fetch_redirect_response=False)
        req = EnrollmentRequest.objects.get()
        self.assertEqual((req.name, req.status, req.course), ("Гульнара", "new", self.course))
        page = self.client.get(reverse("core:enroll_success"))
        self.assertContains(page, "Гульнара")

    def test_invalid_phone_shows_errors(self):
        response = self.client.post(reverse("core:enroll"), {"name": "Test", "phone": "abc"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EnrollmentRequest.objects.exists())

    def test_honeypot_blocks_bots(self):
        response = self.client.post(reverse("core:enroll"), {"name": "Bot", "phone": "+996 700 000 000",
                                                             "website": "http://spam"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(EnrollmentRequest.objects.exists())

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(reverse("core:enroll")).status_code, 405)


class PublicPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.course = Course.objects.create(direction="blender", slug="blender", title_ru="Blender курс",
                                           title_ky="Blender курсу", title_en="Blender course")
        cls.news = News.objects.create(title_ru="Новость", body_ru="Текст")

    def test_pages_open(self):
        for url in ["/", "/courses/", "/courses/?direction=blender", self.course.get_absolute_url(), "/news/",
                    self.news.get_absolute_url(), "/about/", "/contacts/", "/accounts/login/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_hidden_course_is_404(self):
        Course.objects.filter(pk=self.course.pk).update(is_active=False)
        self.assertEqual(self.client.get(self.course.get_absolute_url()).status_code, 404)


class LanguageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.course = Course.objects.create(direction="robotics", slug="robo", title_ru="Робототехника",
                                           title_ky="Робототехника KY", title_en="")

    def test_default_language_is_russian(self):
        response = self.client.get("/")
        self.assertContains(response, 'lang="ru"')
        self.assertContains(response, "Курсы")

    def test_switch_language_sets_cookie(self):
        for code, word in [("ky", "Курстар"), ("en", "Courses"), ("ru", "Курсы")]:
            with self.subTest(code=code):
                response = self.client.post(reverse("set_language"), {"language": code, "next": "/courses/"})
                self.assertRedirects(response, "/courses/", fetch_redirect_response=False)
                self.assertEqual(response.cookies[settings.LANGUAGE_COOKIE_NAME].value, code)
                page = self.client.get("/courses/")
                self.assertContains(page, f'lang="{code}"')
                self.assertContains(page, word)

    def test_kyrgyz_letters_render(self):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "ky"
        self.assertContains(self.client.get("/"), "Жаңы муундун")

    def test_tr_falls_back_to_russian(self):
        with translation.override("ky"):
            self.assertEqual(self.course.tr("title"), "Робототехника KY")
        with translation.override("en"):
            self.assertEqual(self.course.tr("title"), "Робототехника")


class YoutubeTests(TestCase):
    def test_parse_links(self):
        for url in ["https://www.youtube.com/watch?v=zJ-LqeX_fLU", "https://youtu.be/zJ-LqeX_fLU?t=3",
                    "https://www.youtube.com/embed/zJ-LqeX_fLU", "https://youtube.com/shorts/zJ-LqeX_fLU",
                    "https://www.youtube.com/watch?feature=share&v=zJ-LqeX_fLU"]:
            self.assertEqual(youtube_id(url), "zJ-LqeX_fLU")
        self.assertEqual(youtube_id("https://vimeo.com/123"), "")
