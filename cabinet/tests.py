import datetime
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from core.models import Attendance, Course, EnrollmentRequest, Group, Lesson

TEMP_MEDIA = tempfile.mkdtemp(prefix="ngh-test-media-")


def make_user(username, role, **extra):
    user = User(username=username, role=role, first_name=username.title(), **extra)
    user.set_password("pass12345")
    user.save()
    return user


class BaseData(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("admin", User.Role.ADMIN)
        cls.manager = make_user("manager", User.Role.MANAGER)
        cls.teacher = make_user("teacher", User.Role.TEACHER)
        cls.other_teacher = make_user("teacher2", User.Role.TEACHER)
        cls.student = make_user("student", User.Role.STUDENT)
        cls.student2 = make_user("student2", User.Role.STUDENT)
        cls.course = Course.objects.create(direction="robotics", slug="robo", title_ru="Робототехника", price=4500)
        cls.group = Group.objects.create(
            name="ROBO-1", course=cls.course, teacher=cls.teacher, weekdays="0,2",
            start_date=timezone.localdate() - datetime.timedelta(days=60),
        )
        cls.group.students.set([cls.student, cls.student2])
        cls.foreign_group = Group.objects.create(name="ROBO-2", course=cls.course, teacher=cls.other_teacher)

    def login(self, user):
        self.client.force_login(user)


class RoleAccessTests(BaseData):
    CABINETS = {
        User.Role.ADMIN: "cabinet:admin_dashboard",
        User.Role.MANAGER: "cabinet:manager_dashboard",
        User.Role.TEACHER: "cabinet:teacher_dashboard",
        User.Role.STUDENT: "cabinet:student_dashboard",
    }

    def test_anonymous_redirected_to_login(self):
        for name in self.CABINETS.values():
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("accounts:login"), response["Location"])

    def test_cabinet_redirects_by_role(self):
        for user in (self.admin, self.manager, self.teacher, self.student):
            self.login(user)
            response = self.client.get(reverse("cabinet:home"))
            self.assertRedirects(response, reverse(self.CABINETS[user.role]), fetch_redirect_response=False)

    def test_foreign_cabinets_return_403(self):
        for user in (self.manager, self.teacher, self.student):
            self.login(user)
            for role, name in self.CABINETS.items():
                expected = 200 if role == user.role else 403
                with self.subTest(user=user.role, cabinet=role):
                    self.assertEqual(self.client.get(reverse(name)).status_code, expected)

    def test_admin_can_open_every_cabinet(self):
        self.login(self.admin)
        for name in list(self.CABINETS.values()) + ["cabinet:admin_users", "cabinet:manager_requests",
                                                    "cabinet:teacher_lessons", "cabinet:teacher_mark"]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_student_cannot_manage_users(self):
        self.login(self.student)
        self.assertEqual(self.client.get(reverse("cabinet:admin_user_create")).status_code, 403)
        self.assertEqual(self.client.post(reverse("cabinet:admin_user_toggle", args=[self.teacher.pk])).status_code, 403)
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.is_active)

    def test_teacher_sees_only_own_groups(self):
        self.login(self.teacher)
        self.assertEqual(self.client.get(reverse("cabinet:journal_month", args=[self.group.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("cabinet:journal_month", args=[self.foreign_group.pk])).status_code, 403)
        response = self.client.get(reverse("cabinet:teacher_mark"), {"group": self.foreign_group.pk})
        self.assertEqual(response.status_code, 403)

    def test_manager_journal_is_read_only(self):
        self.login(self.manager)
        response = self.client.get(reverse("cabinet:journal_month", args=[self.group.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["can_mark"])
        self.assertEqual(self.client.get(reverse("cabinet:teacher_mark")).status_code, 403)

    def test_blocked_user_cannot_log_in(self):
        self.login(self.admin)
        self.client.post(reverse("cabinet:admin_user_toggle", args=[self.student.pk]))
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)
        self.client.logout()
        self.assertFalse(self.client.login(username="student", password="pass12345"))

    def test_superuser_gets_admin_role(self):
        user = User.objects.create_superuser("root", "root@example.com", "pass12345")
        self.assertEqual(user.role, User.Role.ADMIN)


class AttendanceTests(BaseData):
    def mark(self, day, data):
        payload = {"group": self.group.pk, "date": day.isoformat(), **data}
        return self.client.post(reverse("cabinet:teacher_mark"), payload)

    def test_save_journal(self):
        self.login(self.teacher)
        day = timezone.localdate()
        response = self.mark(day, {
            f"status_{self.student.pk}": "present", f"grade_{self.student.pk}": "5",
            f"status_{self.student2.pk}": "absent", f"grade_{self.student2.pk}": "4",
            f"comment_{self.student2.pk}": "Болел",
        })
        self.assertEqual(response.status_code, 302)
        first = Attendance.objects.get(student=self.student, date=day)
        second = Attendance.objects.get(student=self.student2, date=day)
        self.assertEqual((first.status, first.grade, first.marked_by), ("present", 5, self.teacher))
        # Отсутствующему оценка не ставится.
        self.assertEqual((second.status, second.grade, second.comment), ("absent", None, "Болел"))

    def test_resave_updates_instead_of_duplicating(self):
        self.login(self.teacher)
        day = timezone.localdate()
        self.mark(day, {f"status_{self.student.pk}": "late"})
        self.mark(day, {f"status_{self.student.pk}": "excused"})
        self.assertEqual(Attendance.objects.filter(student=self.student, date=day).count(), 1)
        self.assertEqual(Attendance.objects.get(student=self.student, date=day).status, "excused")

    def test_future_date_and_bad_values_rejected(self):
        self.login(self.teacher)
        self.mark(timezone.localdate() + datetime.timedelta(days=3), {f"status_{self.student.pk}": "present"})
        self.assertFalse(Attendance.objects.exists())
        self.mark(timezone.localdate(), {f"status_{self.student.pk}": "hacked", f"grade_{self.student2.pk}": "99",
                                         f"status_{self.student2.pk}": "present"})
        self.assertFalse(Attendance.objects.filter(student=self.student).exists())
        self.assertIsNone(Attendance.objects.get(student=self.student2).grade)

    def test_other_teacher_cannot_mark_group(self):
        self.login(self.other_teacher)
        response = self.mark(timezone.localdate(), {f"status_{self.student.pk}": "present"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Attendance.objects.exists())

    def test_month_journal_and_export(self):
        day = timezone.localdate()
        Attendance.objects.create(group=self.group, student=self.student, date=day, status="present", grade=5)
        Attendance.objects.create(group=self.group, student=self.student2, date=day, status="absent")
        self.login(self.teacher)
        response = self.client.get(reverse("cabinet:journal_month", args=[self.group.pk]))
        self.assertEqual(response.context["j"]["percent"], 50)
        csv = self.client.get(reverse("cabinet:journal_export", args=[self.group.pk, "csv"]))
        self.assertEqual(csv.status_code, 200)
        self.assertIn("text/csv", csv["Content-Type"])
        xlsx = self.client.get(reverse("cabinet:journal_export", args=[self.group.pk, "xlsx"]))
        self.assertEqual(xlsx.status_code, 200)
        self.assertTrue(xlsx.content.startswith(b"PK"))
        self.assertEqual(self.client.get(reverse("cabinet:journal_export", args=[self.group.pk, "pdf"])).status_code, 404)


@override_settings(MEDIA_ROOT=TEMP_MEDIA, MAX_VIDEO_UPLOAD_MB=1)
class LessonUploadTests(BaseData):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def payload(self, **extra):
        data = {"course": self.course.pk, "group": self.group.pk, "number": 1, "title": "Первый урок",
                "description": "", "is_published": "on"}
        data.update(extra)
        return data

    def test_upload_video_file(self):
        self.login(self.teacher)
        video = SimpleUploadedFile("lesson.mp4", b"\x00\x00\x00\x18ftypmp42" + b"0" * 1024, content_type="video/mp4")
        response = self.client.post(reverse("cabinet:teacher_lesson_create"), self.payload(video_file=video))
        self.assertEqual(response.status_code, 302)
        lesson = Lesson.objects.get()
        self.assertEqual(lesson.teacher, self.teacher)
        self.assertTrue(lesson.video_file.name.endswith(".mp4"))

    def test_ajax_upload_returns_json(self):
        self.login(self.teacher)
        video = SimpleUploadedFile("clip.webm", b"webm" * 100, content_type="video/webm")
        response = self.client.post(
            reverse("cabinet:teacher_lesson_create"), self.payload(video_file=video),
            headers={"x-requested-with": "XMLHttpRequest"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_rejects_wrong_extension_and_size(self):
        self.login(self.teacher)
        bad = SimpleUploadedFile("virus.exe", b"MZ", content_type="application/octet-stream")
        response = self.client.post(reverse("cabinet:teacher_lesson_create"), self.payload(video_file=bad),
                                    headers={"x-requested-with": "XMLHttpRequest"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("video_file", response.json()["errors"])
        big = SimpleUploadedFile("big.mp4", b"0" * (1024 * 1024 + 10), content_type="video/mp4")
        response = self.client.post(reverse("cabinet:teacher_lesson_create"), self.payload(video_file=big))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Lesson.objects.exists())

    def test_youtube_link_and_embed(self):
        self.login(self.teacher)
        self.client.post(reverse("cabinet:teacher_lesson_create"),
                         self.payload(youtube_url="https://youtu.be/zJ-LqeX_fLU"))
        lesson = Lesson.objects.get()
        self.assertEqual(lesson.youtube_embed_url, "https://www.youtube-nocookie.com/embed/zJ-LqeX_fLU?rel=0")

    def test_requires_video_or_link(self):
        self.login(self.teacher)
        response = self.client.post(reverse("cabinet:teacher_lesson_create"), self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Lesson.objects.exists())

    def test_teacher_cannot_edit_foreign_lesson(self):
        lesson = Lesson.objects.create(course=self.course, teacher=self.other_teacher, title="Чужой",
                                       youtube_url="https://youtu.be/zJ-LqeX_fLU")
        self.login(self.teacher)
        self.assertEqual(self.client.get(reverse("cabinet:teacher_lesson_edit", args=[lesson.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("cabinet:teacher_lesson_delete", args=[lesson.pk])).status_code, 403)
        self.assertTrue(Lesson.objects.filter(pk=lesson.pk).exists())

    def test_student_sees_lessons_of_own_groups_only(self):
        mine = Lesson.objects.create(course=self.course, group=self.group, teacher=self.teacher, title="Мой",
                                     youtube_url="https://youtu.be/zJ-LqeX_fLU")
        foreign = Lesson.objects.create(course=self.course, group=self.foreign_group, teacher=self.other_teacher,
                                        title="Чужой", youtube_url="https://youtu.be/zJ-LqeX_fLU")
        self.login(self.student)
        self.assertEqual(self.client.get(reverse("cabinet:lesson_detail", args=[mine.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("cabinet:lesson_detail", args=[foreign.pk])).status_code, 403)


class ManagerTests(BaseData):
    def test_create_student_from_request(self):
        req = EnrollmentRequest.objects.create(name="Айбек Асанов", phone="+996 555 000 111", course=self.course)
        self.login(self.manager)
        response = self.client.get(reverse("cabinet:manager_request_to_student", args=[req.pk]))
        self.assertEqual(response.context["form"].initial["username"], "aibek.asanov")
        response = self.client.post(reverse("cabinet:manager_request_to_student", args=[req.pk]), {
            "first_name": "Айбек", "last_name": "Асанов", "username": "aibek.asanov", "phone": req.phone,
            "is_active": "on", "groups_field": [self.group.pk],
        })
        self.assertEqual(response.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.status, EnrollmentRequest.Status.ENROLLED)
        self.assertEqual(req.student.role, User.Role.STUDENT)
        self.assertIn(self.group, req.student.study_groups.all())

    def test_quick_status_change(self):
        req = EnrollmentRequest.objects.create(name="Test", phone="+996 555 000 111")
        self.login(self.manager)
        self.client.post(reverse("cabinet:manager_request_status", args=[req.pk]), {"status": "contacted"})
        req.refresh_from_db()
        self.assertEqual((req.status, req.handled_by), ("contacted", self.manager))
