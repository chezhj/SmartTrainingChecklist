import factory

from checklist.models import Attribute, CheckItem, Procedure


class AttributeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Attribute

    title = factory.Faker("word")
    order = factory.Sequence(lambda n: n)
    description = factory.Faker("paragraph")
    show = True  # Default value for the show field
    over_ruled_by = None  # Default value for the over_ruled_by field


class ProcedureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Procedure

    title = factory.Faker("sentence")
    step = factory.Sequence(lambda n: n)
    slug = factory.Faker("slug")


class CheckItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CheckItem

    item = factory.Faker("word")
    procedure = factory.SubFactory(ProcedureFactory, __sequence=10)
    step = factory.Sequence(lambda n: n)
    setting = factory.Faker("sentence")

    @factory.post_generation
    def attributes(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for attribute in extracted:
                self.attributes.add(attribute)
