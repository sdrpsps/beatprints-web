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

CatalogProvider = Literal["deezer", "spotify"]
SearchProvider = Literal["deezer", "spotify", "all"]
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
                "平台标识或二维码。使用 Spotify 数据源并选择 spotify 时，"
                "可以省略 platform_links.spotify。每张海报只显示一个平台，"
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


class SearchAlbumSummary(BaseModel):
    """歌曲所属专辑的简要信息。"""

    id: Annotated[
        int | str,
        Field(
            description="数据源中的专辑 ID。Deezer 使用整数，Spotify 使用字符串。",
            examples=["614LGcMwiEpyQ5SVg6S5Im"],
        ),
    ]
    title: Annotated[
        str,
        Field(
            description="歌曲所属专辑标题。",
            examples=["Summer Breeze"],
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
            examples=["7lp5evZr7qEDwlv5PS8b6i"],
        ),
    ]
    provider: Annotated[
        Literal["deezer", "spotify"],
        Field(
            description="结果的数据来源。",
            examples=["spotify"],
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
        Field(description="歌手名称列表。", examples=[["Piper"]]),
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
            examples=["https://open.spotify.com/track/7lp5evZr7qEDwlv5PS8b6i"],
        ),
    ]
    release_date: Annotated[
        str | None,
        Field(
            description=(
                "当前匹配版本的发行日期。通常为 YYYY-MM-DD；"
                "Spotify 在精度不足时也可能只返回 YYYY 或 YYYY-MM。"
            ),
            examples=["1983-05-01"],
        ),
    ] = None
    release_year: Annotated[
        int | None,
        Field(
            description="从 release_date 提取的年份，便于前端显示和筛选。",
            examples=[1983],
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
        Field(description="歌曲时长，单位为秒；专辑结果中不返回。", examples=[203]),
    ] = None
    duration: Annotated[
        str | None,
        Field(
            description="便于前端直接显示的歌曲时长；专辑结果中不返回。",
            examples=["03:23"],
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


class LyricsLine(BaseModel):
    """前端歌词选择器中的一条规范化非空歌词。"""

    index: Annotated[
        int,
        Field(
            ge=1,
            description="规范化后的歌词行号，从 1 开始。",
            examples=[1],
        ),
    ]
    text: Annotated[
        str,
        Field(
            min_length=1,
            max_length=1000,
            description="去除首尾空白后的歌词文本。",
            examples=["There was a time"],
        ),
    ]


class LyricsPreviewData(BaseModel):
    """供前端选择最多四行可选歌词使用的预览结果。"""

    provider: CatalogProvider
    catalog_id: int | str
    instrumental: Annotated[
        bool,
        Field(description="LRClib 是否将当前歌曲标记为纯音乐。"),
    ]
    lines: Annotated[
        list[LyricsLine],
        Field(
            description=(
                "按原歌词顺序返回的非空歌词。纯音乐时为空；"
                "前端默认不选中歌词，允许选择最多四行。"
            ),
        ),
    ]


class PlatformLinkMatchData(BaseModel):
    """目标音乐平台中歌曲或专辑的规范公开链接及当前资料。"""

    url: HttpUrl
    title: str
    artists: list[str]
    type: Literal["track", "album"]
    album: str | None = None
    release_year: int | None = None
    duration_seconds: int | None = None
    track_count: int | None = None
    cover_url: HttpUrl | None = None


class PlatformMatchOptionsData(BaseModel):
    """One destination lookup, split into an optional confirmation and ranked choices."""

    match: PlatformLinkMatchData | None = None
    candidates: list[PlatformLinkMatchData] = Field(default_factory=list)
