from marshmallow import Schema, fields, validate


class ConfigExtrasSchema(Schema):
    background = fields.URL()
    background_transparancy = fields.Integer()
    font_color = fields.String()
    logo = fields.URL()
    color = fields.String()
    rating_min_fb = fields.Integer()
    greetings = fields.String()
    closing = fields.String()
    enable_redirect = fields.Boolean()
    additional_comment_instruction = fields.String()
    custom_comment_wording = fields.String()
    closing_button_text = fields.String()
    disable_rating_instruction = fields.Boolean()


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
    extras = fields.Nested(ConfigExtrasSchema)


app_config_schema = AppConfigSchema()
app_configs_schema = AppConfigSchema(many=True)
