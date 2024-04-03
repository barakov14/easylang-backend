from marshmallow import Schema, fields, validate


class InvitationCodeSchema(Schema):
    id = fields.Int(dump_only=True)
    code = fields.Str(dump_only=True)
    role = fields.Str(required=True)


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True)
    name = fields.Str(required=False, validate=validate.Length(min=1))
    surname = fields.Str(required=False, validate=validate.Length(min=1))
    role = fields.Str(required=False, dump_only=True, validate=validate.OneOf(["manager", "editor", "translator"]))
    rate = fields.Int(required=False, validate=validate.Range(min=0), dump_only=True)
    status = fields.Str(validate=validate.OneOf(['ready', 'not_ready']), dump_only=True)
    password = fields.Str(required=True, load_only=True)


class RegisterUserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True)
    name = fields.Str(required=False, validate=validate.Length(min=1))
    surname = fields.Str(required=False, validate=validate.Length(min=1))
    invitation_code = fields.Str(required=True)
    role = fields.Str(required=False, dump_only=True, validate=validate.OneOf(["manager", "editor", "translator"]))
    rate = fields.Int(required=False, validate=validate.Range(min=0), dump_only=True)
    status = fields.Str(validate=validate.OneOf(['ready', 'not_ready']), dump_only=True)
    password = fields.Str(required=True, load_only=True)


class LoginUserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True)
    name = fields.Str(required=False, dump_only=True, validate=validate.Length(min=1))
    surname = fields.Str(required=False, dump_only=True, validate=validate.Length(min=1))
    role = fields.Str(required=False, dump_only=True, validate=validate.OneOf(["manager", "editor", "translator"]))
    rate = fields.Int(required=False, dump_only=True, validate=validate.Range(min=0))
    status = fields.Str(dump_only=True, validate=validate.OneOf(['ready', 'not_ready']))
    password = fields.Str(required=True, load_only=True)


class TaskSubmissionSchema(Schema):
    id = fields.Int(dump_only=True)
    text = fields.Str(required=True)
    grade = fields.Float(dump_only=True)
    status = fields.Str(dump_only=True, validate=validate.OneOf(
        ['in_process', 'delaying', 'checking', 'done', 'may_be_delayed', 'delayed']))


class TaskSubmissionCheckingSchema(Schema):
    id = fields.Int(dump_only=True)
    text = fields.Str(required=True)
    grade = fields.Int(required=True)
    status = fields.Str(dump_only=True, validate=validate.OneOf(
        ['in_process', 'delaying', 'checking', 'ready', 'may_be_delayed', 'delayed']))


class CreateTaskSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1))
    description = fields.Str(required=True, validate=validate.Length(min=1))
    status = fields.Str(dump_only=True, validate=validate.OneOf(['in_process', 'ready', 'checking', 'delaying']),
                        default='in_process')
    started_at = fields.String(dump_only=True)
    progress = fields.Float(default=0, dump_only=True)
    success = fields.Integer(dump_only=True)
    deadline = fields.String(required=True)
    responsibles = fields.List(fields.Nested(UserSchema), dump_only=True)
    submissions = fields.List(fields.Nested(TaskSubmissionSchema), dump_only=True)


class ReadTaskSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1))
    description = fields.Str(required=True, validate=validate.Length(min=1))
    status = fields.Str(dump_only=True, validate=validate.OneOf(['in_process', 'ready', 'delaying']),
                        default='in_process')
    started_at = fields.String(dump_only=True)
    progress = fields.Float(default=0, dump_only=True)
    success = fields.Integer(dump_only=True)
    deadline = fields.String(required=True)
    responsibles = fields.List(fields.Nested(UserSchema), dump_only=True)
    submissions = fields.List(fields.Nested(TaskSubmissionSchema), dump_only=True)


class CreateProjectSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1))
    description = fields.Str(required=True, validate=validate.Length(min=1))
    status = fields.Str(dump_only=True, validate=validate.OneOf(['in_process', 'ready', 'may_be_delayed', 'delayed']),
                        default='in_process')
    started_at = fields.String(dump_only=True)
    progress = fields.Float(default=0, dump_only=True)
    number_of_chapters = fields.Integer(required=True)
    ended_at = fields.String(dump_only=True)
    editors = fields.List(fields.Nested(UserSchema), dump_only=True)
    tasks = fields.List(fields.Nested(CreateTaskSchema), dump_only=True)


class ReadProjectSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1))
    description = fields.Str(required=True, validate=validate.Length(min=1))
    status = fields.Str(dump_only=True, validate=validate.OneOf(['in_process', 'ready', 'may_be_delayed', 'delayed']),
                        default='in_process')
    started_at = fields.String(dump_only=True)
    progress = fields.Float(default=0, dump_only=True)
    ended_at = fields.String(dump_only=True)
    number_of_chapters = fields.Integer(dump_only=True)
    # editors = fields.List(fields.Nested(UserSchema), dump_only=True)
    # tasks = fields.List(fields.Nested(ReadTaskSchema), dump_only=True)


class NotificationSchema(Schema):
    id = fields.Int(dump_only=True)
    project_id = fields.Int(dump_only=True)
    project_name = fields.Str(dump_only=True)
    status = fields.Str(dump_only=True, validate=validate.OneOf(
        ['in_process', 'delaying', 'checking', 'ready', 'may_be_delayed', 'delayed']))
