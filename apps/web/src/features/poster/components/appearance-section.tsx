import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldTitle,
} from "@/components/ui/field"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import {
  SectionHeading,
  studioSectionClass,
  type Studio,
} from "@/features/poster/components/studio-shared"
import { zhCN } from "@/features/poster/copy"
import type { Theme } from "@/features/poster/types"

const themeItems = [
  { value: "Light", label: "Light · 明亮" },
  { value: "Dark", label: "Dark · 深色" },
  { value: "Catppuccin", label: "Catppuccin" },
  { value: "Gruvbox", label: "Gruvbox" },
  { value: "Nord", label: "Nord" },
  { value: "RosePine", label: "Rosé Pine" },
  { value: "Everforest", label: "Everforest" },
] satisfies { value: Theme; label: string }[]

export function AppearanceSection({ studio }: { studio: Studio }) {
  if (!studio.selected) return null
  return (
    <section className={studioSectionClass}>
      <SectionHeading
        number={studio.kind === "track" ? "04" : "03"}
        title={zhCN.appearance}
        description="选择生成器支持的主题，并决定是否使用封面提取的底部强调色。"
      />
      <FieldGroup>
        <ThemeField studio={studio} />
        <OptionSwitch
          id="accent"
          title="封面强调色"
          description="在海报底部加入从封面提取的色彩。"
          checked={studio.accent}
          onChange={studio.setAccent}
        />
        {studio.kind === "album" ? (
          <>
            <OptionSwitch
              id="indexing"
              title="显示曲目编号"
              description="在曲目名称前显示 1.、2. 等序号。"
              checked={studio.indexing}
              onChange={studio.setIndexing}
            />
            <OptionSwitch
              id="shuffle"
              title="随机曲序"
              description="每次生成前重新排列曲目，成品顺序可能不同。"
              checked={studio.shuffle}
              onChange={studio.setShuffle}
            />
          </>
        ) : null}
      </FieldGroup>
    </section>
  )
}

function ThemeField({ studio }: { studio: Studio }) {
  return (
    <Field orientation="responsive">
      <FieldTitle>海报主题</FieldTitle>
      <Select
        items={themeItems}
        value={studio.theme}
        onValueChange={(value) => value && studio.setTheme(value as Theme)}
      >
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent alignItemWithTrigger={false}>
          <SelectGroup>
            {themeItems.map((item) => (
              <SelectItem key={item.value} value={item.value}>
                {item.label}
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
    </Field>
  )
}

function OptionSwitch({
  id,
  title,
  description,
  checked,
  onChange,
}: {
  id: string
  title: string
  description: string
  checked: boolean
  onChange: (value: boolean) => void
}) {
  return (
    <Field orientation="horizontal">
      <FieldLabel htmlFor={id}>
        <FieldTitle>{title}</FieldTitle>
        <FieldDescription>{description}</FieldDescription>
      </FieldLabel>
      <Switch id={id} checked={checked} onCheckedChange={onChange} />
    </Field>
  )
}
