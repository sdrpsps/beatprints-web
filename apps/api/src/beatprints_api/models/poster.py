from typing import Annotated, Literal

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, HttpUrl, RootModel, model_validator

Theme = Annotated[
    Literal[
        "Light",
        "Dark",
        "Catppuccin",
        "Gruvbox",
        "Nord",
        "RosePine",
        "Everforest",
    ],
    Field(
        description="海报配色主题。",
        examples=["Light"],
    ),
]

# Source catalogs are runtime-registered integrations.  Keeping these values as
# strings lets a newly enabled adapter use the unchanged public request schema.
CatalogProvider = str
SearchProvider = str
PosterPlatform = str


class PosterPlatformLinks(RootModel[dict[str, AnyUrl]]):
    """Destination-keyed public links for the one QR code on a poster."""

    @model_validator(mode="after")
    def require_at_least_one_link(self) -> "PosterPlatformLinks":
        if not self.root:
            raise ValueError("platform_links must contain at least one platform URL")
        return self


class TrackMetadataInput(BaseModel):
    """调用方完全自定义的歌曲资料。"""

    title: Annotated[
        str,
        Field(
            min_length=1,
            max_length=300,
            description="歌曲标题。",
            examples=["Summer Breeze"],
        ),
    ]
    artists: Annotated[
        list[str],
        Field(
            min_length=1,
            max_length=20,
            description="参与歌曲的歌手名称列表。",
            examples=[["Piper"]],
        ),
    ]
    album: Annotated[
        str,
        Field(
            min_length=1,
            max_length=300,
            description="歌曲所属专辑。",
            examples=["Summer Breeze"],
        ),
    ]
    released: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            description="显示在海报上的发行日期，可以使用任意可读格式。",
            examples=["May 1, 1983"],
        ),
    ]
    duration: Annotated[
        str,
        Field(
            pattern=r"^\d{1,3}:\d{2}$",
            description="歌曲时长，格式为 分钟:秒。",
            examples=["03:23"],
        ),
    ]
    cover_url: Annotated[
        HttpUrl,
        Field(
            description="公网封面地址，仅支持 JPEG、PNG、WebP，最大 15 MB。",
            examples=["https://example.com/summer-breeze.jpg"],
        ),
    ]
    label: Annotated[
        str,
        Field(
            min_length=1,
            max_length=300,
            description="唱片公司或发行厂牌。",
            examples=["Light In The Attic Records"],
        ),
    ]


class AlbumMetadataInput(BaseModel):
    """调用方完全自定义的专辑资料。"""

    title: Annotated[
        str,
        Field(
            min_length=1,
            max_length=300,
            description="专辑标题。",
            examples=["Summer Breeze"],
        ),
    ]
    artists: Annotated[
        list[str],
        Field(
            min_length=1,
            max_length=20,
            description="专辑歌手名称列表。",
            examples=[["Piper"]],
        ),
    ]
    released: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            description="显示在海报上的发行日期。",
            examples=["May 1, 1983"],
        ),
    ]
    tracks: Annotated[
        list[str],
        Field(
            min_length=1,
            max_length=100,
            description="按展示顺序排列的专辑曲目名称。",
            examples=[["Shine On", "Summer Breeze", "Hot Sand", "Gentle Shower"]],
        ),
    ]
    cover_url: Annotated[
        HttpUrl,
        Field(
            description="公网封面地址，仅支持 JPEG、PNG、WebP，最大 15 MB。",
            examples=["https://example.com/summer-breeze-album.jpg"],
        ),
    ]
    label: Annotated[
        str,
        Field(
            min_length=1,
            max_length=300,
            description="唱片公司或发行厂牌。",
            examples=["Light In The Attic Records"],
        ),
    ]


class PosterSource(BaseModel):
    provider: Annotated[
        CatalogProvider | None,
        Field(
            description=(
                "query 或 catalog_id 使用的音乐平台。以后新增平台时沿用此字段，"
                "无需改变生成接口结构。"
            ),
            examples=["spotify"],
        ),
    ] = None
    query: Annotated[
        str | None,
        Field(
            min_length=1,
            max_length=500,
            description=(
                "在 provider 指定的平台中搜索并使用第一条结果；"
                "不能与 catalog_id、metadata 同时提供。"
            ),
            examples=["Summer Breeze Piper"],
        ),
    ] = None
    catalog_id: Annotated[
        int | str | None,
        Field(
            description=(
                "由 /v1/search 返回的平台歌曲或专辑 ID，必须和 provider 配套使用；"
                "不能与 query、metadata 同时提供。"
            ),
            examples=[
                "7lp5evZr7qEDwlv5PS8b6i",
                "614LGcMwiEpyQ5SVg6S5Im",
            ],
        ),
    ] = None
    platform_links: Annotated[
        PosterPlatformLinks | None,
        Field(
            description=(
                "各音乐平台的歌曲或专辑直达链接。只有同时通过 qr_platform "
                "明确选择一个平台时才会在海报上渲染二维码；未选中的链接只保存"
                "在请求中，不会同时渲染。"
            )
        ),
    ] = None
    qr_platform: Annotated[
        PosterPlatform | None,
        Field(
            description=(
                "明确选择要在海报左下角显示二维码的平台；不提供时不显示任何"
                "平台标识或二维码。若所选目的地声明可复用来源链接，可省略对应"
                "platform_links。每张海报只显示一个平台，"
                "二维码和平台名称使用从封面提取并经过对比度保护的颜色。"
            ),
            examples=["spotify"],
        ),
    ] = None

    @model_validator(mode="after")
    def validate_qr_platform_link(self) -> "PosterSource":
        if self.qr_platform is None:
            return self
        values = self.platform_links.root if self.platform_links is not None else {}
        source_link_may_be_reused = (
            self.qr_platform == self.provider and getattr(self, "metadata", None) is None
        )
        if self.qr_platform not in values and not source_link_may_be_reused:
            raise ValueError(
                f"platform_links.{self.qr_platform} is required for "
                f"qr_platform={self.qr_platform}"
            )
        return self

    def validate_source(self, metadata: object | None) -> None:
        supplied = sum(
            value is not None for value in (self.query, self.catalog_id, metadata)
        )
        if supplied != 1:
            raise ValueError(
                "Exactly one of query, catalog_id, or metadata must be supplied"
            )
        if metadata is None and not self.provider:
            raise ValueError("provider is required when query or catalog_id is supplied")


class TrackPosterRequest(PosterSource):
    """歌曲海报请求。query、catalog_id、metadata 三选一。"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "provider": "spotify",
                "query": "Summer Breeze Piper",
                "platform_links": {
                    "apple_music": (
                        "https://music.apple.com/us/album/summer-breeze/1790520587"
                    ),
                    "qq_music": "https://y.qq.com/n/ryqq/songDetail/001example",
                },
                "qr_platform": "apple_music",
                "theme": "Light",
                "accent": True,
            }
        }
    )

    metadata: Annotated[
        TrackMetadataInput | None,
        Field(
            description=(
                "完全自定义歌曲资料；提供后不会访问音乐平台，"
                "且不能与 query、catalog_id 同时提供。"
            )
        ),
    ] = None
    lyrics: Annotated[
        str | None,
        Field(
            max_length=2000,
            description=(
                "直接显示在海报上的可选歌词。提供后不会查询 LRClib，"
                "并优先于 lyrics_range。空字符串表示不显示歌词，最多四行。"
            ),
            examples=["", "First line\nSecond line\nThird line\nFourth line"],
        ),
    ] = None
    lyrics_range: Annotated[
        str | None,
        Field(
            pattern=r"^[1-9]\d*-[1-9]\d*$",
            description=(
                "未提供 lyrics 时，从 LRClib 歌词中选取的行号范围；"
                "范围内必须恰好有四行非空歌词。"
            ),
            examples=["11-14"],
        ),
    ] = None
    instrumental_text: Annotated[
        str,
        Field(
            max_length=200,
            description=(
                "检测到纯音乐时显示的可选短句。空字符串表示不显示歌词区域文字。"
            ),
            examples=["", "献给没有歌词的夜晚"],
        ),
    ] = ""
    accent: Annotated[
        bool,
        Field(
            description="是否在海报底部增加从封面提取的强调色。",
            examples=[True],
        ),
    ] = False
    theme: Theme = "Light"

    @model_validator(mode="after")
    def check_source(self) -> "TrackPosterRequest":
        self.validate_source(self.metadata)
        if self.lyrics is not None and len(self.lyrics.splitlines()) > 4:
            raise ValueError("lyrics must contain at most four lines")
        if len(self.instrumental_text.splitlines()) > 4:
            raise ValueError("instrumental_text must contain at most four lines")
        return self


class AlbumPosterRequest(PosterSource):
    """专辑海报请求。query、catalog_id、metadata 三选一。"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "provider": "spotify",
                "query": "Summer Breeze Piper",
                "platform_links": {
                    "netease_music": "https://music.163.com/album?id=123456",
                },
                "qr_platform": "netease_music",
                "theme": "Light",
                "accent": True,
                "indexing": True,
                "shuffle": False,
            }
        }
    )

    metadata: Annotated[
        AlbumMetadataInput | None,
        Field(
            description=(
                "完全自定义专辑资料；提供后不会访问音乐平台，"
                "且不能与 query、catalog_id 同时提供。"
            )
        ),
    ] = None
    indexing: Annotated[
        bool,
        Field(
            description="是否在曲目名称前显示 1.、2. 等序号。",
            examples=[True],
        ),
    ] = False
    shuffle: Annotated[
        bool,
        Field(
            description="是否在生成前随机打乱曲目顺序。",
            examples=[False],
        ),
    ] = False
    accent: Annotated[
        bool,
        Field(
            description="是否在海报底部增加从封面提取的强调色。",
            examples=[True],
        ),
    ] = False
    theme: Theme = "Light"

    @model_validator(mode="after")
    def check_source(self) -> "AlbumPosterRequest":
        self.validate_source(self.metadata)
        return self
