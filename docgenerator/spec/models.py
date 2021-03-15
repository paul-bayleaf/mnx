from django.db import models
from django.urls import reverse

class DataType(models.Model):
    name = models.CharField(max_length=80)
    slug = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)
    xsd_name = models.CharField(max_length=80, blank=True,
        verbose_name='XSD name',
        help_text='Use this field if this data type is a native XSD type such as string.'
    )
    base_type = models.ForeignKey('self', blank=True, null=True, on_delete=models.CASCADE, related_name='+')
    union_types = models.ManyToManyField('self', blank=True, related_name='+',
        help_text='If this data type is a union of multiple other types, list them here.'
    )

    class Meta:
        db_table = 'data_types'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('data_type_detail', args=(self.slug,))

class DataTypeOption(models.Model):
    data_type = models.ForeignKey(DataType, on_delete=models.CASCADE)
    value = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'data_type_options'

class Concept(models.Model):
    name = models.CharField(max_length=100)
    slug = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        db_table = 'concepts'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('concept_detail', args=(self.slug,))

class DocumentFormat(models.Model):
    name = models.CharField(max_length=100)
    slug = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'document_formats'

    def __str__(self):
        return self.name

    def comparison_url(self):
        return reverse('format_comparison_detail', args=(self.slug,))

class XMLElement(models.Model):
    name = models.CharField(max_length=80)
    slug = models.CharField(max_length=80, unique=True)
    base_element = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    is_abstract_element = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    content_data_type = models.ForeignKey(DataType, null=True, blank=True, on_delete=models.SET_NULL)
    is_featured = models.BooleanField(default=False)
    attribute_groups = models.ManyToManyField('XMLAttributeGroup', blank=True)

    class Meta:
        db_table = 'xml_elements'
        verbose_name = 'XML element'
        verbose_name_plural = 'XML elements'

    def __str__(self):
        return self.slug

    def get_absolute_url(self):
        return reverse('element_detail', args=(self.slug,))

    def name_with_brackets(self):
        return f'<{self.name}>'

    def get_content_data_type(self):
        if self.content_data_type:
            return self.content_data_type
        if self.base_element:
            return self.base_element.get_content_data_type()
        return None

    def get_child_elements(self):
        result = []
        for child in XMLElement.objects.filter(child_rel__parent=self):
            if child.is_abstract_element:
                result.extend(child.get_child_elements())
            else:
                result.append(child)
        if self.base_element:
            result.extend(self.base_element.get_child_elements())
        return sorted(set(result), key=lambda el: el.name)

    def get_parent_elements(self):
        result = []
        for parent in XMLElement.objects.filter(parent_rel__child=self):
            if parent.is_abstract_element:
                result.extend(parent.get_parent_elements())
                for parent_subclass in XMLElement.objects.filter(base_element=parent):
                    if not parent_subclass.is_abstract_element:
                        result.append(parent_subclass)
            else:
                result.append(parent)
        return sorted(set(result), key=lambda el: el.name)

    def get_all_base_elements(self):
        result = []
        if self.base_element:
            result.append(self.base_element)
            result.extend(self.base_element.get_all_base_elements())
        return result

class XMLAttributeGroup(models.Model):
    name = models.CharField(max_length=300, unique=True)

    class Meta:
        db_table = 'xml_attribute_groups'
        verbose_name = 'XML attribute group'
        verbose_name_plural = 'XML attribute groups'

    def __str__(self):
        return self.name

class XMLAttribute(models.Model):
    element = models.ForeignKey(XMLElement, on_delete=models.CASCADE, null=True)
    attribute_group = models.ForeignKey(XMLAttributeGroup, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=80)
    is_required = models.BooleanField()
    description = models.TextField(blank=True)
    data_type = models.ForeignKey(DataType, on_delete=models.PROTECT)

    class Meta:
        db_table = 'xml_attributes'
        verbose_name = 'XML attribute'
        verbose_name_plural = 'XML attributes'

    def __str__(self):
        return self.name

class XMLRelationship(models.Model):
    parent = models.ForeignKey(XMLElement, on_delete=models.CASCADE, related_name='parent_rel')
    child = models.ForeignKey(XMLElement, on_delete=models.CASCADE, related_name='child_rel')
    min_amount = models.IntegerField(null=True, blank=True)
    max_amount = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'xml_relationships'
        verbose_name = 'XML relationship'
        verbose_name_plural = 'XML relationships'

class ExampleDocument(models.Model):
    name = models.CharField(max_length=300)
    slug = models.CharField(max_length=100, unique=True)
    blurb = models.TextField(blank=True)
    document = models.TextField()
    image_url = models.CharField(max_length=300, blank=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        db_table = 'example_documents'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from spec.utils.datautils import update_example_elements
        update_example_elements(self)

    def get_absolute_url(self):
        return reverse('example_detail', args=(self.slug,))

class ExampleDocumentConcept(models.Model):
    example = models.ForeignKey(ExampleDocument, on_delete=models.CASCADE)
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE)

    class Meta:
        db_table = 'example_concepts'

class ExampleDocumentComparison(models.Model):
    example = models.ForeignKey(ExampleDocument, on_delete=models.CASCADE)
    doc_format = models.ForeignKey(DocumentFormat, on_delete=models.CASCADE)
    preamble = models.TextField(blank=True)
    document = models.TextField()
    position = models.SmallIntegerField()

    class Meta:
        db_table = 'example_comparisons'

    def get_absolute_url(self):
        return self.doc_format.comparison_url() + f'#{self.example.slug}'

    def preamble_html(self):
        if self.preamble:
            return '\n'.join(f'<p class="examplenotes">{line}</p>' for line in self.preamble.split('\n') if line)
        return ''

class ExampleDocumentElement(models.Model):
    # This is a cache of each element used in each
    # ExampleDocument. It's updated via ExampleDocument.save().
    example = models.ForeignKey(ExampleDocument, on_delete=models.CASCADE)
    element_name = models.CharField(max_length=80)

    class Meta:
        db_table = 'example_elements'

class ElementConcept(models.Model):
    element = models.ForeignKey(XMLElement, on_delete=models.CASCADE)
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE)

    class Meta:
        db_table = 'element_concepts'
