from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

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

CatalogProvider = Literal["deezer", "spotify"]
SearchProvider = Literal["deezer", "spotify", "all"]


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
            examples=[["Seals and Crofts"]],
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
            examples=["September 4, 1972"],
        ),
    ]
    duration: Annotated[
        str,
        Field(
            pattern=r"^\d{1,3}:\d{2}$",
            description="歌曲时长，格式为 分钟:秒。",
            examples=["03:25"],
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
            examples=["Warner Records"],
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
            examples=[["Seals & Crofts"]],
        ),
    ]
    released: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            description="显示在海报上的发行日期。",
            examples=["September 4, 1972"],
        ),
    ]
    tracks: Annotated[
        list[str],
        Field(
            min_length=1,
            max_length=100,
            description="按展示顺序排列的专辑曲目名称。",
            examples=[["Hummingbird", "Funny Little Man", "Say"]],
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
            examples=["Warner Records"],
        ),
    ]


class PosterSource(BaseModel):
    provider: Annotated[
        CatalogProvider,
        Field(
            description=(
                "query 或 catalog_id 使用的音乐平台。以后新增平台时沿用此字段，"
                "无需改变生成接口结构。"
            ),
            examples=["spotify"],
        ),
    ] = "spotify"
    query: Annotated[
        str | None,
        Field(
            min_length=1,
            max_length=500,
            description=(
                "在 provider 指定的平台中搜索并使用第一条结果；"
                "不能与 catalog_id、metadata 同时提供。"
            ),
            examples=["Summer Breeze Seals and Crofts"],
        ),
    ] = None
    catalog_id: Annotated[
        int | str | None,
        Field(
            description=(
                "由 /v1/search 返回的平台歌曲或专辑 ID，必须和 provider 配套使用；"
                "不能与 query、metadata 同时提供。"
            ),
            examples=["3B0ms7Xlxl16tRztKHpcu9"],
        ),
    ] = None

    def validate_source(self, metadata: object | None) -> None:
        supplied = sum(
            value is not None for value in (self.query, self.catalog_id, metadata)
        )
        if supplied != 1:
            raise ValueError(
                "Exactly one of query, catalog_id, or metadata must be supplied"
            )


class TrackPosterRequest(PosterSource):
    """歌曲海报请求。query、catalog_id、metadata 三选一。"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "provider": "spotify",
                "catalog_id": "3B0ms7Xlxl16tRztKHpcu9",
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
            min_length=1,
            max_length=2000,
            description=(
                "直接显示在海报上的歌词。提供后不会查询 LRClib，"
                "并优先于 lyrics_range。建议提供四行。"
            ),
            examples=["First line\nSecond line\nThird line\nFourth line"],
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
            min_length=1,
            max_length=200,
            description="检测到纯音乐时显示的替代文字。",
            examples=["It's an instrumental track :>"],
        ),
    ] = "It's an instrumental track :>"
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
        return self


class AlbumPosterRequest(PosterSource):
    """专辑海报请求。query、catalog_id、metadata 三选一。"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "provider": "spotify",
                "catalog_id": "1Ugdi2OTxKopVVqsprp5pb",
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


class SearchAlbumSummary(BaseModel):
    """歌曲所属专辑的简要信息。"""

    id: Annotated[
        int | str,
        Field(
            description="数据源中的专辑 ID。Deezer 使用整数，Spotify 使用字符串。",
            examples=[496095, "1Ugdi2OTxKopVVqsprp5pb"],
        ),
    ]
    title: Annotated[
        str,
        Field(
            description="歌曲所属专辑标题。",
            examples=["Seals & Crofts' Greatest Hits"],
        ),
    ]


class SearchResult(BaseModel):
    """适合在前端搜索结果卡片中直接展示的音乐目录资料。"""

    id: Annotated[
        int | str,
        Field(
            description=(
                "数据源中的结果 ID。将它与 provider 一起作为生成接口的 "
                "catalog_id，即可获取同一平台的海报资料。"
            ),
            examples=[5416564, "3B0ms7Xlxl16tRztKHpcu9"],
        ),
    ]
    provider: Annotated[
        Literal["deezer", "spotify"],
        Field(
            description="结果的数据来源。",
            examples=["deezer"],
        ),
    ]
    type: Annotated[
        Literal["track", "album"],
        Field(description="结果类型：track 表示歌曲，album 表示专辑。"),
    ]
    title: Annotated[
        str,
        Field(description="歌曲或专辑标题。", examples=["Summer Breeze"]),
    ]
    artists: Annotated[
        list[str],
        Field(description="歌手名称列表。", examples=[["Seals and Crofts"]]),
    ]
    cover_url: Annotated[
        HttpUrl,
        Field(
            description="适合搜索结果预览和后续展示的高清封面地址。",
            examples=[
                (
                    "https://cdn-images.dzcdn.net/images/cover/"
                    "acc4d1fcd78e408aab27e59811bd8981/"
                    "1000x1000-000000-80-0-0.jpg"
                )
            ],
        ),
    ]
    link: Annotated[
        HttpUrl,
        Field(
            description="数据源中的歌曲或专辑网页地址。",
            examples=["https://www.deezer.com/track/5416564"],
        ),
    ]
    release_date: Annotated[
        str | None,
        Field(
            description=(
                "当前匹配版本的发行日期。通常为 YYYY-MM-DD；"
                "Spotify 在精度不足时也可能只返回 YYYY 或 YYYY-MM。"
            ),
            examples=["1977-10-11"],
        ),
    ] = None
    release_year: Annotated[
        int | None,
        Field(
            description="从 release_date 提取的年份，便于前端显示和筛选。",
            examples=[1977],
        ),
    ] = None
    release_date_precision: Annotated[
        Literal["year", "month", "day"] | None,
        Field(
            description="发布日期精度；Spotify 会明确返回，Deezer 固定为 day。",
            examples=["day"],
        ),
    ] = None
    album: Annotated[
        SearchAlbumSummary | None,
        Field(description="歌曲所属专辑；专辑搜索结果中不返回此字段。"),
    ] = None
    duration_seconds: Annotated[
        int | None,
        Field(description="歌曲时长，单位为秒；专辑结果中不返回。", examples=[205]),
    ] = None
    duration: Annotated[
        str | None,
        Field(
            description="便于前端直接显示的歌曲时长；专辑结果中不返回。",
            examples=["03:25"],
        ),
    ] = None
    explicit: Annotated[
        bool | None,
        Field(description="是否被数据源标记为显式内容。", examples=[False]),
    ] = None
    track_count: Annotated[
        int | None,
        Field(description="专辑曲目数量；歌曲结果中不返回。", examples=[10]),
    ] = None
    isrc: Annotated[
        str | None,
        Field(
            description="歌曲的国际标准录音代码；专辑结果中不返回。",
            examples=["USWB19901645"],
        ),
    ] = None
