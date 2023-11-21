import factory

from checklist.models import Attribute, CheckItem, Procedure


class AttributeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Attribute
        skip_postgeneration_save = True

    title = factory.Faker("word")
    order = factory.Sequence(lambda n: n)
    description = factory.Faker("paragraph")
    show = True  # Default value for the show field
    over_ruled_by = None  # Default value for the over_ruled_by field

    @factory.post_generation
    def set_over_ruled_by(self, create, extracted, **kwargs):
        # The create flag allows you to conditionally set the over_ruled_by
        # attribute only when the object is being created. If you don't include
        # this check and try to set the over_ruled_by attribute without the
        # create flag, it could lead to unnecessary updates to the
        # database for existing objects when you use Factory Boy.

        if not create:
            # If this is not a create call, do nothing
            return

        if extracted:
            # If an 'over_ruled_by' attribute was provided, set the ForeignKey
            self.over_ruled_by = extracted
            self.save()


class ProcedureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Procedure

    title = factory.Faker("sentence")
    step = factory.Sequence(lambda n: n)
    slug = factory.Faker("slug")


class CheckItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CheckItem
        skip_postgeneration_save = True

    item = factory.Faker("word")
    procedure = factory.SubFactory(ProcedureFactory, __sequence=30)
    step = factory.Sequence(lambda n: n)
    setting = factory.Faker("sentence")

    @factory.post_generation
    def attributes(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for attribute in extracted:
                self.attributes.add(attribute)
            self.save()
