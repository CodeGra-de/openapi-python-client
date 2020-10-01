# {{ project_name }}
{{ description }}

## Usage
First, create a client:

```python
from {{ package_name }} import setup

# Don't store this in plaintext in your code!
client = setup(
    username="my_username",
    password="my_password",
    host="https://app.codegra.de",
)
```

Now call your endpoint and use your models:

```python
from {{ package_name }}.models import PatchCourseData

courses = client.course.get_all()
for course in courses:
    client.course.patch(
        PatchCourseData(name=course.name + ' (NEW)'),
        course_id=course.id,
    )
```

## Installing
This project uses [Poetry](https://python-poetry.org/) to manage dependencies
and packaging. Currently you will need to install it using poetry, but in the
future we will start releasing this package on pypi.
