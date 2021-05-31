import enum


class EmojiRating(enum.Enum):
    PUAS = 'Puas'
    TIDAK_PUAS = 'Tidak Puas'

class EmojiRatingType(enum.Enum):
    THUMB = 'thumb'
    FACE = 'face'