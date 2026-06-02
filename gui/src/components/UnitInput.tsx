import {
  Autocomplete,
  Box,
  FormControl,
  FormHelperText,
  FormLabel,
  Input
} from "@mui/joy"
import { ReactNode, useId } from "react"
import InfoOutlined from "@mui/icons-material/InfoOutlined"
import { SxProps } from "@mui/joy/styles/types"

/* ───────────────────────────────────────────── */
/* UNIT TYPES                                 */
/* ───────────────────────────────────────────── */

export type UnitType = "length" | "viscosity" | "unitless"

export type UnitProps = {
  label?: string
  description?: string
  defaultValue?: string | undefined
  value?: string | undefined
  error?: string | undefined
  warning?: string | undefined
  placeholder?: string | undefined
  autocompleteValues?: undefined | number[]
  explainIcon?: undefined | ReactNode
  sx?: SxProps
  marginY?: string | number

  unitType?: UnitType

  onChange?: (fieldValue: string, parsedValue: number | undefined) => void
}

/* ───────────────────────────────────────────── */
/* UNIT PARSER                                */
/* ───────────────────────────────────────────── */

function parseWithUnits(raw: string, unitType: UnitType): number | undefined {
  if (!raw) return undefined
  const cleaned = raw.trim().toLowerCase()

  // ───── UNITLESS (e.g. dilution, ratios) ─────
  if (unitType === "unitless") {
    const v = parseFloat(cleaned)
    return isNaN(v) ? undefined : v
  }

  // ───── GENERAL NUMBER + UNIT ─────
  const re = /^([+-]?\d*\.?\d+(?:e[+-]?\d+)?)(\s*[a-zμμ·\/]+)?$/i
  const match = cleaned.match(re)
  if (!match) return undefined

  const value = parseFloat(match[1])
  if (isNaN(value)) return undefined

  const unit = match[2]?.trim()

  // ───── LENGTH → canonical µm ─────
  if (unitType === "length") {
    if (!unit || unit === "µm" || unit === "um" || unit === "μm") return value
    if (unit === "mm") return value * 1000
    if (unit === "nm") return value / 1000
    return undefined
  }

  // ───── VISCOSITY → canonical Pa·s ─────
  if (unitType === "viscosity") {
    if (!unit || unit === "pa·s" || unit === "pas") return value
    if (unit === "mpa·s" || unit === "mpas" || unit === "cp")
      return value * 1e-3
    return undefined
  }

  return undefined
}

/* ───────────────────────────────────────────── */
/* COMPONENT                                 */
/* ───────────────────────────────────────────── */

export function UnitInput(props: UnitProps) {
  const id = useId()
  const unitType = props.unitType ?? "length"

  const unitLabel =
    unitType === "length" ? "µm" :
    unitType === "viscosity" ? "Pa·s" :
    ""

  const handleValueChange = (value: string) => {
    const parsed = parseWithUnits(value, unitType)
    props.onChange?.(value, parsed)
  }

  const shared = {
    value: props.value,
    placeholder: props.placeholder ?? props.label,
    id,
    defaultValue: props.defaultValue,
    sx: {
      "& input": { textAlign: "right" },
      ...props.sx
    },
    startDecorator: props.explainIcon
      ? <Box sx={{ width: "3em", height: "3em", margin: 1 }}>
          {props.explainIcon}
        </Box>
      : undefined,
    endDecorator: unitLabel
  }

  const field =
    props.autocompleteValues !== undefined ? (
      <Autocomplete
        freeSolo
        disableClearable
        options={props.autocompleteValues.map(o => o.toString())}
        inputValue={props.value}
        {...shared}
        onInputChange={(_, value) => {
          if (value !== null) handleValueChange(value)
        }}
      />
    ) : (
      <Input
        {...shared}
        onChange={e => handleValueChange(e.target.value)}
        style={{ flexGrow: 1 }}
      />
    )

  return (
    <FormControl
      {...(props.error !== undefined ? { error: true } : {})}
      sx={{
        marginY: props.marginY ?? 2,
        flexGrow: 1
      }}
      color={props.warning ? "warning" : undefined}
    >
      {props.label && <FormLabel htmlFor={id}>{props.label}</FormLabel>}

      {field}

      {/* Description */}
      {props.description && !props.error && !props.warning && (
        <FormHelperText sx={{ marginX: 0 }}>
          {props.description}
        </FormHelperText>
      )}

      {/* Error */}
      {props.error && (
        <FormHelperText sx={{ marginX: 0 }}>
          <InfoOutlined />
          {props.error}
        </FormHelperText>
      )}

      {/* Warning */}
      {props.warning && (
        <FormHelperText sx={{ marginX: 0 }}>
          <InfoOutlined color="warning" />
          {props.warning}
        </FormHelperText>
      )}
    </FormControl>
  )
}
