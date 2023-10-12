# pylint: disable=no-member
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
"""
Test classes for model.py
"""

from django.db import IntegrityError
from django.forms import ValidationError
from django.test import TestCase
from django.utils.text import slugify

# Create your tests here.
from checklist.models import CheckItem
from checklist.models import Procedure
from checklist.models import Attribute


class TestCheckItem(TestCase):
    profile_list = []

    def setUp(self):
        default_procedure = Procedure.objects.create(title="procedure one", step=1)
        Attribute.objects.create(title="left", order=1)
        Attribute.objects.create(title="right", order=2)
        Attribute.objects.create(title="center", order=3)
        self.profile_list.append(Attribute.objects.get(title="left").id)

        CheckItem.objects.create(item="item one", procedure=default_procedure, step=3)
        CheckItem.objects.create(item="item two", procedure=default_procedure, step=1)
        CheckItem.objects.create(item="item three", procedure=default_procedure, step=5)

    def test_order_checkitem(self):
        items = CheckItem.objects.all()
        self.assertEqual(items[0].step, 1)
        self.assertEqual(items[1].step, 3)
        self.assertEqual(items[2].step, 5)

    def test_str_checkitem(self):
        item = CheckItem.objects.get(item="item three")
        self.assertEqual(str(item), item.item)

    def test_negative_step(self):
        procedure = CheckItem.objects.get(item="item three").procedure
        with self.assertRaises(IntegrityError):
            CheckItem.objects.create(item="item three", procedure=procedure, step=-5)

    def test_cascade_delete(self):
        item = CheckItem.objects.get(item="item three")
        item.procedure.delete()
        with self.assertRaises(CheckItem.DoesNotExist):
            item.refresh_from_db()

    def test_toolong_itemname(self):
        procedure = CheckItem.objects.get(item="item three").procedure
        too_long_string = "item name" * 10
        item = CheckItem.objects.create(
            item=too_long_string, procedure=procedure, step=8
        )
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_toolong_setting(self):
        procedure = CheckItem.objects.get(item="item three").procedure
        too_long_string = "item name" * 10
        item = CheckItem.objects.create(item="test item", procedure=procedure, step=8)
        item.setting = too_long_string
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_shouldshow_with_no_attributes(self):
        item = CheckItem.objects.get(item="item three")
        self.assertTrue(item.shouldshow(self.profile_list))

    def test_shouldshow_with_matching_attributes(self):
        item = CheckItem.objects.get(item="item three")
        item.attributes.add(Attribute.objects.get(title="left"))
        self.assertTrue(item.shouldshow(self.profile_list))

    def test_should_not_show_with_none_matching_attributes(self):
        item = CheckItem.objects.get(item="item three")
        item.attributes.add(Attribute.objects.get(title="right"))
        self.assertFalse(item.shouldshow(self.profile_list))

    def test_should_show_with_one_matching_attributes(self):
        item = CheckItem.objects.get(item="item three")
        item.attributes.add(Attribute.objects.get(title="right"))
        # prepare profile with two attributes
        self.profile_list.append(Attribute.objects.get(title="right").id)

        self.assertTrue(item.shouldshow(self.profile_list))

    def test_should_show_with_all_matching_attributes(self):
        item = CheckItem.objects.get(item="item three")
        item.attributes.add(Attribute.objects.get(title="right"))
        item.attributes.add(Attribute.objects.get(title="left"))
        # prepare profile with two attributes
        self.profile_list.append(Attribute.objects.get(title="right").id)

        self.assertTrue(item.shouldshow(self.profile_list))

    def test_should_not_show_with_two_and_one_matching_attributes(self):
        item = CheckItem.objects.get(item="item three")
        item.attributes.add(Attribute.objects.get(title="right"))
        item.attributes.add(Attribute.objects.get(title="left"))
        # prepare profile with two attributes

        self.assertFalse(item.shouldshow(self.profile_list))


class TestProcedure(TestCase):
    def setUp(self):
        default_procedure = Procedure.objects.create(title="procedure one", step=1)
        default_procedure.slug = slugify(default_procedure.title)
        default_procedure.step = 4
        default_procedure.save()

        CheckItem.objects.create(item="item one", procedure=default_procedure, step=3)
        CheckItem.objects.create(item="item two", procedure=default_procedure, step=1)
        CheckItem.objects.create(item="item three", procedure=default_procedure, step=5)

    def test_str_procedure(self):
        proc = Procedure.objects.get(title="procedure one")
        self.assertEqual(str(proc), proc.title)

    def test_get_absolute_url(self):
        proc = Procedure.objects.get(title="procedure one")
        self.assertEqual(proc.get_absolute_url(), "/" + proc.slug)


class TestAttribute(TestCase):
    def test_title_as_string(self):
        self.att = Attribute.objects.create(title="left", order=1)
        self.assertEquals(str(self.att), self.att.title)

    def test_default_color(self):
        att = Attribute.objects.create(title="dummy", order=2)
        self.assertEquals(att.btn_color, "#194D33")
