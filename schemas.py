from marshmallow import Schema, fields, validate


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True)
    name = fields.Str(required=False, validate=validate.Length(min=1))
    email = fields.Str(required=True, validate=validate.Email())
    surname = fields.Str(required=False, validate=validate.Length(min=1))
    role = fields.Str(dump_only=True, validate=validate.OneOf(["manager", "editor", "translator", "admin"]))
    status = fields.Str(dump_only=True, validate=validate.OneOf(['READY', 'NOT READY']))
    password = fields.Str(required=True, load_only=True)
    tasks_completed = fields.Int(required=False, dump_only=True)
    tasks_evaluated = fields.Int(required=False, dump_only=True)
    projects_created = fields.Int(required=False, dump_only=True)
    projects_completed = fields.Int(required=False, dump_only=True)
    rate = fields.Int(required=False, dump_only=True)


class RegisterUserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True)
    name = fields.Str(required=True, validate=validate.Length(min=1))
    surname = fields.Str(required=True, validate=validate.Length(min=1))
    email = fields.Str(required=True, validate=validate.Email())
    role = fields.Str(required=True, validate=validate.OneOf(["manager", "editor", "translator", "admin"]))
    status = fields.Str(dump_only=True, validate=validate.OneOf(['READY', 'NOT READY']))
    password = fields.Str(required=True, load_only=True)


class LoginUserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True)
    name = fields.Str(dump_only=True, validate=validate.Length(min=1))
    email = fields.Str(dump_only=True, validate=validate.Email())
    surname = fields.Str(dump_only=True, validate=validate.Length(min=1))
    role = fields.Str(dump_only=True, validate=validate.OneOf(["manager", "editor", "translator", "admin"]))
    status = fields.Str(dump_only=True, validate=validate.OneOf(['READY', 'NOT READY']))
    password = fields.Str(required=True, load_only=True)


class TaskSubmissionSchema(Schema):
    id = fields.Int(dump_only=True)
    text = fields.Str(required=True)
    pages_done = fields.Int(required=True)
    translator_id = fields.Int(dump_only=True)
    comment = fields.Str(dump_only=True)
    grade = fields.Float(dump_only=True)
    status = fields.Str(dump_only=True, validate=validate.OneOf(
        ['IN PROGRESS', 'MAY BE DELAYED', 'IN VERIFYING', 'NOT APPROVED', 'APPROVED']))


class TaskSubmissionSchemaSendForCorrection(Schema):
    comment = fields.Str(required=True)

class TaskSubmissionCheckingSchema(Schema):
    id = fields.Int(dump_only=True)
    text = fields.Str(dump_only=True)
    grade = fields.Int(required=True)
    translator_id = fields.Int(dump_only=True)
    status = fields.Str(dump_only=True, validate=validate.OneOf(
        ['IN PROGRESS', 'MAY BE DELAYED', 'IN VERIFYING', 'NOT APPROVED', 'APPROVED']))

class SetTaskDeadlineSchema(Schema):
    deadline = fields.String(required=True)

class CreateTaskSchema(Schema):
    id = fields.Int(dump_only=True)
    code = fields.Int(dump_only=True)
    rejected = fields.Str(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1))
    description = fields.Str(required=True, validate=validate.Length(min=1))
    status = fields.Str(dump_only=True, validate=validate.OneOf(
        ['IN PROGRESS', 'MAY BE DELAYED', 'IN VERIFYING', 'NOT APPROVED', 'APPROVED']),
                        default='IN PROGRESS')
    started_at = fields.String(dump_only=True)
    progress = fields.Float(default=0, dump_only=True)
    pages = fields.Integer(required=True)
    deadline = fields.String(dump_only=True)
    responsibles = fields.List(fields.Nested(UserSchema), dump_only=True)
    submissions = fields.List(fields.Nested(TaskSubmissionSchema), dump_only=True)


class ReadTaskSchema(Schema):
    id = fields.Int(dump_only=True)
    code = fields.Int(dump_only=True)
    rejected = fields.Str(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1))
    description = fields.Str(required=True, validate=validate.Length(min=1))
    status = fields.Str(dump_only=True, validate=validate.OneOf(['IN PROGRESS', 'FINISHED', 'MAY BE DELAYED']),
                        default='IN PROGRESS')
    started_at = fields.String(dump_only=True)
    progress = fields.Float(default=0, dump_only=True)
    pages = fields.Integer(required=True)
    deadline = fields.String(required=False, dump_only=True)
    responsibles = fields.List(fields.Nested(UserSchema), dump_only=True)
    submissions = fields.List(fields.Nested(TaskSubmissionSchema), dump_only=True)


class DeadlineSchema(Schema):
    deadline = fields.String(required=True)

class CreateProjectSchema(Schema):
    id = fields.Int(dump_only=True)
    code = fields.Str(dump_only=True)
    color = fields.Str(required=True)
    name = fields.Str(required=True, validate=validate.Length(min=1))
    description = fields.Str(required=True, validate=validate.Length(min=1))
    status = fields.Str(dump_only=True, validate=validate.OneOf(['NEW', 'IN PROGRESS', 'MAY BE DELAYED', 'FINISHED']),
                        default='NEW')
    started_at = fields.String(dump_only=True)
    progress = fields.Float(default=0, dump_only=True)
    number_of_pages = fields.Integer(required=True)
    creator_id = fields.String(dump_only=True)
    deadline = fields.String(required=True)
    ended_at = fields.String(dump_only=True)
    editors = fields.List(fields.Nested(UserSchema), dump_only=True)
    tasks = fields.List(fields.Nested(CreateTaskSchema), dump_only=True)
    creators = fields.List(fields.Nested(UserSchema), dump_only=True)


class ReadProjectSchema(Schema):
    id = fields.Int(dump_only=True)
    code = fields.Str(dump_only=True)
    color = fields.Str(required=True)
    name = fields.Str(required=True, validate=validate.Length(min=1))
    description = fields.Str(required=True, validate=validate.Length(min=1))
    status = fields.Str(dump_only=True, validate=validate.OneOf(['NEW', 'IN PROGRESS', 'MAY BE DELAYED', 'FINISHED']),)
    started_at = fields.String(dump_only=True)
    progress = fields.Float(default=0, dump_only=True)
    ended_at = fields.String(dump_only=True)
    deadline = fields.String(dump_only=True)
    number_of_pages = fields.Integer(dump_only=True)
    creators = fields.List(fields.Nested(UserSchema), dump_only=True)
    editors = fields.List(fields.Nested(UserSchema), dump_only=True)
    tasks = fields.List(fields.Nested(ReadTaskSchema), dump_only=True)
    translators = fields.List(fields.Nested(UserSchema), dump_only=True)


class UpdateProjectSchema(Schema):
    id = fields.Int(dump_only=True)
    code = fields.Str(dump_only=True)

    name = fields.Str(required=True, validate=validate.Length(min=1))
    description = fields.Str(required=True, validate=validate.Length(min=1))
    status = fields.Str(dump_only=True, validate=validate.OneOf(['IN PROGRESS', 'MAY BE DELAYED', 'FINISHED']),
                        default='IN PROGRESS')
    started_at = fields.String(dump_only=True)
    progress = fields.Float(default=0, dump_only=True)
    ended_at = fields.String(dump_only=True)
    number_of_pages = fields.Integer(dump_only=True)
    creator_id = fields.String(dump_only=True)
    editors = fields.List(fields.Nested(UserSchema), dump_only=True)
    tasks = fields.List(fields.Nested(ReadTaskSchema), dump_only=True)
    translators = fields.List(fields.Nested(UserSchema), dump_only=True)

class NotificationSchema(Schema):
    id = fields.Int(dump_only=True)
    count = fields.Int(dump_only=True)
    project_id = fields.Int(required=True)
    link = fields.Str(required=True, dump_only=True)
    project_name = fields.Str(required=True)
    status = fields.Str(required=True, validate=validate.OneOf(['IN PROGRESS', 'MAY BE DELAYED', 'FINISHED']))
    msg = fields.Str(required=True)


class NotificationCountSchema(Schema):
    notifications_count = fields.Int(dump_only=True, required=True)


class UserRoleSchema(Schema):
    role = fields.Str(required=True, validate=validate.OneOf(["manager", "editor", "translator"]))


class ProjectsListQueryArgsSchema(Schema):
    filter = fields.Str(description="Filter projects by name, id, or description")
    status = fields.Str(description="Filter projects by status",
                        validate=validate.OneOf(['IN PROGRESS', 'MAY BE DELAYED', 'FINISHED']))
    sort_by_date = fields.Str(description="Sort projects by date", validate=validate.OneOf(['asc', 'desc']))


class UserListQueryArgsSchema(Schema):
    name = fields.Str(description="Filter users by name")
    id = fields.Int(description="Filter users by ID")
    role = fields.Str(description="Filter users by role")


class TaskSubmissionFilterSchema(Schema):
    status = fields.Str(description="Filter submissions by status",
                        validate=validate.OneOf(
                            ['IN PROGRESS', 'MAY BE DELAYED', 'IN VERIFYING', 'NOT APPROVED', 'APPROVED']))
