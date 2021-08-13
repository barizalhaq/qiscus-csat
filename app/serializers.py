from marshmallow import Schema, fields, validate, validates_schema, ValidationError, validates
from .utils.enums import EmojiRatingType


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
    submit_button_text = fields.String()
    hide_app_name_title = fields.Boolean()
    ignore_source = fields.String()  # list of number
    closing_page_after_csat_submitted = fields.Boolean()
    emoji_type = fields.String()


class AppConfigSchema(Schema):
    id = fields.Integer(dump_only=True)
    app_code = fields.String(required=True)
    app_name = fields.String(required=True)
    admin_email = fields.String(required=True)
    admin_token = fields.String(required=True)

    official_web = fields.URL()
    csat_msg = fields.String(required=True)
    rating_type = fields.String(
        validate=validate.OneOf(['star', 'number', 'custom', 'emoji']), required=True)
    rating_total = fields.Integer(required=True)
    extras = fields.Nested(ConfigExtrasSchema)
    csat_page = fields.String()
    emoji_type = fields.String(
        validate=validate.OneOf(
            [EmojiRatingType.THUMB.value, EmojiRatingType.FACE.value]),
        required=False
    )

    @validates_schema
    def emoji_type_required_if_rating_is_emoji(self, data, **kwargs):
        if data['rating_type'] == 'emoji':
            if 'emoji_type' not in data or data['emoji_type'] is None:
                raise ValidationError(
                    'Emoji type is required when rating type is emoji')


class AttachAppSchema(Schema):
    id = fields.Integer(dump_only=True)
    app_code = fields.String(required=True)
    app_name = fields.String(required=True)
    admin_email = fields.String(required=True)
    admin_token = fields.String(required=True)
    app_secret = fields.String(required=False)


class ConfigSchema(Schema):
    official_web = fields.URL()
    csat_msg = fields.String(required=True)
    rating_type = fields.String(
        allow_none=True, validate=validate.OneOf(['star', 'number', 'emoji']))
    rating_total = fields.Integer(allow_none=True)
    extras = fields.Nested(ConfigExtrasSchema, allow_none=True)
    csat_page = fields.String(allow_none=True)
    emoji_type = fields.String(
        validate=validate.OneOf(
            [EmojiRatingType.THUMB.value, EmojiRatingType.FACE.value]),
        allow_none=True
    )

    @validates_schema
    def emoji_type_required_if_rating_is_emoji(self, data, **kwargs):
        if data['rating_type'] == 'emoji':
            if 'emoji_type' not in data:
                raise ValidationError(
                    'Emoji type is required when rating type is emoji')


app_config_schema = AppConfigSchema()
app_configs_schema = AppConfigSchema(many=True)
attach_app_schema = AttachAppSchema()
config_app_schema = ConfigSchema()


class CsatSchema(Schema):
    class Meta:
        fields = ('id', 'csat_code', 'user_id', 'rating', 'feedback',
                  'agent_email', 'source', 'submitted_at', 'app_id')


csat_schema = CsatSchema()
csats_schema = CsatSchema(many=True)


class Config(Schema):
    rating_type = fields.String()

    class Meta:
        fields = ('official_web', 'csat_msg', 'rating_total',
                  'extras', 'csat_page', 'rating_type')


config_schema = Config()
