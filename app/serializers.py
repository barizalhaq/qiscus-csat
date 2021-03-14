from marshmallow import Schema, fields, validate


class ConfigExtrasSchema(Schema):
    background = fields.URL(required=True)
    logo = fields.URL(required=True)
    color = fields.String()
    rating_min_fb = fields.Integer()


class AppConfigSchema(Schema):
    id = fields.Integer(dump_only=True)
    app_code = fields.String(required=True)
    app_name = fields.String(required=True)
    admin_email = fields.String(required=True)
    admin_token = fields.String(required=True)

    official_web = fields.URL()
    csat_msg = fields.String(required=True)
    rating_type = fields.String(
        validate=validate.OneOf(['star', 'number']), required=True)
    rating_total = fields.Integer(required=True)
    extras = fields.Nested(ConfigExtrasSchema, required=True)


app_config_schema = AppConfigSchema()
app_configs_schema = AppConfigSchema(many=True)
