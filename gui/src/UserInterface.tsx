import { useState } from "react"
import {
  Accordion,
  AccordionDetails,
  AccordionGroup,
  AccordionSummary,
  Box,
  Button,
  CircularProgress,
  FormControl,
  FormLabel,
  Option,
  Select,
  Stack,
  Switch,
  Typography,
  useTheme
} from "@mui/joy"
import PlayCircleFilledWhiteIcon from "@mui/icons-material/PlayCircleFilledWhite"
import OutputIcon from "@mui/icons-material/Output"
import { InfoOutlined } from "@mui/icons-material"

import { UnitInput } from "./components/UnitInput"
import { ContentBox } from "./components/ContentBox"
import { MMFTIcon } from "./icons/MMFTIcon"

/* ───────────────────────────────────────────── */
/*                                  */
/* ───────────────────────────────────────────── */

export type InputParameters = {
  twoGradients: boolean
  modulesX: number
  modulesY: number
  dilutionX: number
  dilutionY: number
  viscosity: number
  channelWidth: number
  channelHeight: number
  viaDiameter: number
  gridResolution: number

  layerSwitchDistance: number
  chipSizeX: number
  chipSizeY: number
  chipSideSpacing: number
  spacingX: number
  spacingY: number
  spacingOut: number
}

export type InputState = {
  parameters: InputParameters
  errors?: string[]
}

export type OutputState = {
  error?: string
  resultFile?: string
  previewUrl?: string
  jobId?: string
  dxfFiles?: Array<{ name: string; url: string }>
}

/* ───────────────────────────────────────────── */
/* 2. DEFAULT VALUES                          */
/* ───────────────────────────────────────────── */

const defaultInputState: InputState = { // length units in micrometers, everything else in SI
  parameters: {
    twoGradients: true,
    modulesX: 3,
    modulesY: 1,
    dilutionX: 0.1,
    dilutionY: 0.1,
    viscosity: 1e-3,
    channelWidth: 150,
    channelHeight: 150,
    viaDiameter: 700,
    gridResolution: 100,

    layerSwitchDistance: 1162,
    chipSizeX: 127760,
    chipSizeY: 85480,
    chipSideSpacing: 7000,
    spacingX: 2000,
    spacingY: 800,
    spacingOut: 800
    },
  errors: undefined
}

const defaultOutputState: OutputState = {
  error: undefined,
  resultFile: undefined
}

/* ───────────────────────────────────────────── */
/* 3. MAIN UI COMPONENT                       */
/* ───────────────────────────────────────────── */

export function UserInterface() {
  const theme = useTheme()

  const [input, setInput] = useState<InputState>(defaultInputState)
  const [output, setOutput] = useState<OutputState>(defaultOutputState)
  const [nonce, setNonce] = useState(1)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isUpdatingPreview, setIsUpdatingPreview] = useState(false)
  const [colorByFlow, setColorByFlow] = useState(false)
  const [selectedDxfUrl, setSelectedDxfUrl] = useState<string | null>(null)
  const [chipSizePreset, setChipSizePreset] = useState<"vertical" | "horizontal">("horizontal")

  const showModuleWarning =
  input.parameters.modulesX > 3 || input.parameters.modulesY > 3

  const showMinModuleWarning =
    input.parameters.modulesX < 1 || input.parameters.modulesY < 1

  const applyChipSizePreset = (preset: "vertical" | "horizontal") => {
    const vertical = { x: 85480, y: 127760 }
    const next = preset === "vertical" ? vertical : { x: vertical.y, y: vertical.x }

    setChipSizePreset(preset)
    setInput(s => ({
      ...s,
      parameters: {
        ...s.parameters,
        chipSizeX: next.x,
        chipSizeY: next.y,
      },
    }))
  }

  /* ───────────────────────────────────────────── */
  /*  STATE HELPERS                              */
  /* ───────────────────────────────────────────── */

  const updateParameter = (key: keyof InputParameters, value: number) => {
    setInput(s => ({
      ...s,
      parameters: {
        ...s.parameters,
        [key]: value
      }
    }))
  }

  /* ───────────────────────────────────────────── */
  /* GENERATE DESIGN (CALL BACKEND)              */
  /* ───────────────────────────────────────────── */

  const generateDesign = async () => {
    setIsGenerating(true)
    setOutput({ error: undefined, resultFile: undefined, previewUrl: undefined, jobId: undefined, dxfFiles: undefined })
    setSelectedDxfUrl(null)

    try {
      const response = await fetch("api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...input.parameters, colorByFlow }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || "Generation failed")
      }

      const result = await response.json()
      setOutput({
        resultFile: result.dxfUrl,
        previewUrl: result.previewUrl,
        jobId: result.jobId,
        dxfFiles: result.dxfFiles,
      })

      if (Array.isArray(result.dxfFiles) && result.dxfFiles.length > 0) {
        setSelectedDxfUrl(result.dxfFiles[0].url)
      }
    } catch (err: any) {
      setOutput({ error: err.message })
    } finally {
      setIsGenerating(false)
    }
  }

  const updatePreview = async (nextColorByFlow: boolean) => {
    if (!output.jobId) {
      setColorByFlow(nextColorByFlow)
      return
    }

    setColorByFlow(nextColorByFlow)
    setIsUpdatingPreview(true)
    try {
      const res = await fetch(`api/preview/${output.jobId}?colorByFlow=${nextColorByFlow ? "true" : "false"}`, {
        method: "POST",
      })
      if (!res.ok) {
        const error = await res.json().catch(() => ({}))
        throw new Error(error.detail || "Failed to update preview")
      }
      const data = await res.json()
      setOutput(o => ({ ...o, previewUrl: data.previewUrl }))
      setNonce(n => n + 1)
    } catch (err: any) {
      setOutput(o => ({ ...o, error: err.message }))
    } finally {
      setIsUpdatingPreview(false)
    }
  }

  /* ───────────────────────────────────────────── */
  /*  UI                                        */
  /* ───────────────────────────────────────────── */

  return (
    <div
      style={{
        backgroundColor: theme.vars.palette.background.level1,
        minHeight: "100vh",
        display: "flex",
        // gap: 2,
        flexDirection: "column"
      }}
    >
      {/* ───────── HEADER ───────── */}
      <header
        style={{
          backgroundColor: theme.vars.palette.primary[500],
          display: "flex",
          justifyContent: "center"
        }}
      >
        <Box>
          <MMFTIcon
            primaryColor={theme.vars.palette.common.white}
            secondaryColor={`hsl(from ${theme.vars.palette.primary[500]} h s calc(l * 2.3))`}
            height="8em"
            style={{
              verticalAlign: "middle"
            }}
          />
          <Typography
            level="h1"
            sx={{
              color: theme.vars.palette.common.white,
              fontSize: "2rem",
              paddingY: 1,
              display: "inline-block",
              verticalAlign: "middle"
            }}
          >
            <span style={{ fontSize: "1.15em", fontWeight: 900 }}>N</span>etwork-aware{" "}
            <span style={{ fontSize: "1.15em", fontWeight: 900 }}>O</span>ptimization
            <br />
             by{" "}
            <span style={{ fontSize: "1.15em", fontWeight: 900 }}>R</span>esistance{" "}
            <span style={{ fontSize: "1.15em", fontWeight: 900 }}>A</span>djustment
          </Typography>
        </Box>
      </header>

      {/* ───────── MAIN ───────── */}
      <main>
        <Box
          sx={{
            maxWidth: "900px",   // match mmft-routing-block GUI visually
            mx: "auto",          // horizontal centering
            display: "flex",
            flexDirection: "column",
            gap: 2,
            textAlign: "left"    // prevents centered form labels
          }}
        >
          <Typography sx={{ my: 2 }}>
            Configure and generate multi-gradient microfluidic chips that host Organ-on-Chip modules. To apply the network optimization to other microfluidic networks, simply define your network and run the code using the source code available on GitHub.          </Typography>

          <AccordionGroup>

          {/* ───────── MODULE SETTINGS ───────── */}
          <Accordion>
            <AccordionSummary>
              <Typography level="h4">Number of Modules</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Stack direction="row" spacing={3}>
                <UnitInput
                  label="Modules X"
                  unitType="unitless"
                  value={String(input.parameters.modulesX)}
                  onChange={(_, v) => updateParameter("modulesX", v ?? 0)}
                />
                <UnitInput
                  label="Modules Y"
                  unitType="unitless"
                  value={String(input.parameters.modulesY)}
                  onChange={(_, v) => updateParameter("modulesY", v ?? 0)}
                />
              </Stack>
                {showMinModuleWarning && (
                  <Typography
                    level="body-sm"
                    startDecorator={<InfoOutlined />}
                    sx={{ color: theme.vars.palette.danger[500] }}
                  >
                    At least 1 module is required in both X and Y.
                  </Typography>
                )}
                {showModuleWarning && (
                  <Typography
                    level="body-sm"
                    startDecorator={<InfoOutlined />}
                    sx={{ color: theme.vars.palette.warning[500] }}
                  >
                    Warning: Using more than 3 modules in either X or Y may not be supported with the current initialization.
                  </Typography>
                )}
            {/* </Stack> */}
            </AccordionDetails>
          </Accordion>

          {/* ───────── DILUTION SETTINGS ───────── */}
          <Accordion>
            <AccordionSummary>
              <Typography level="h4">Dilution</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Stack direction="row" spacing={3}>
                <UnitInput
                  label="Dilution X"
                  unitType="unitless"
                  allowDecimal
                  value={String(input.parameters.dilutionX)}
                  onChange={(_, v) => updateParameter("dilutionX", v ?? 0)}
                />
                <UnitInput
                  label="Dilution Y"
                  unitType="unitless"
                  allowDecimal
                  value={String(input.parameters.dilutionY)}
                  onChange={(_, v) => updateParameter("dilutionY", v ?? 0)}
                />
              </Stack>
            </AccordionDetails>
          </Accordion>

          {/* ───────── FLUID SETTINGS ───────── */}
          <Accordion>
            <AccordionSummary>
              <Typography level="h4">Fluid</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <UnitInput
                label="Viscosity"
                unitType="viscosity"
                allowDecimal
                value={String(input.parameters.viscosity)}
                onChange={(_, v) => updateParameter("viscosity", v ?? 0)}
              />
            </AccordionDetails>
          </Accordion>

          {/* ───────── CHANNEL GEOMETRY ───────── */}
          <Accordion>
            <AccordionSummary>
              <Typography level="h4">Channel Geometry</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Stack direction="row" spacing={3}>
                <UnitInput
                  label="Channel Width"
                  unitType="length"
                  value={String(input.parameters.channelWidth)}
                  onChange={(_, v) => updateParameter("channelWidth", v ?? 0)}
                />
                <UnitInput
                  label="Channel Height"
                  unitType="length"
                  value={String(input.parameters.channelHeight)}
                  onChange={(_, v) => updateParameter("channelHeight", v ?? 0)}
                />
                <UnitInput
                  label="Via Diameter"
                  unitType="length"
                  value={String(input.parameters.viaDiameter)}
                  onChange={(_, v) => updateParameter("viaDiameter", v ?? 0)}
                />
              </Stack>
            </AccordionDetails>
          </Accordion>

          {/* ───────── CHIP GEOMETRY ───────── */}
          <Accordion>
            <AccordionSummary>
              <Typography level="h4">Chip Geometry</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Stack spacing={1}>
                <Stack direction="row" spacing={3}>
                  <UnitInput
                    label="Layer Switch Distance"
                    unitType="length"
                    value={String(input.parameters.layerSwitchDistance)}
                    onChange={(_, v) => updateParameter("layerSwitchDistance", v ?? 0)}
                  />
                  <UnitInput
                    label="Side Spacing"
                    unitType="length"
                    value={String(input.parameters.chipSideSpacing)}
                    onChange={(_, v) => updateParameter("chipSideSpacing", v ?? 0)}
                  />
                </Stack>

                <FormControl>
                  <FormLabel>Chip size</FormLabel>
                  <Select
                    value={chipSizePreset}
                    onChange={(_, v) => {
                      const preset = v === "horizontal" ? "horizontal" : "vertical"
                      applyChipSizePreset(preset)
                    }}
                  >
                    <Option value="vertical">Standard well plate format (vertical, 127.76 mm × 85.48 mm)</Option>
                    <Option value="horizontal">Standard well plate format (horizontal, 85.48 mm × 127.76 mm)</Option>
                  </Select>
                </FormControl>

                <Stack direction="row" spacing={3}>
                  <UnitInput
                    label="Module Spacing X"
                    unitType="length"
                    value={String(input.parameters.spacingX)}
                    onChange={(_, v) => updateParameter("spacingX", v ?? 0)}
                  />
                  <UnitInput
                    label="Module Spacing Y"
                    unitType="length"
                    value={String(input.parameters.spacingY)}
                    onChange={(_, v) => updateParameter("spacingY", v ?? 0)}
                  />
                  <UnitInput
                    label="Outflow Spacing"
                    unitType="length"
                    value={String(input.parameters.spacingOut)}
                    onChange={(_, v) => updateParameter("spacingOut", v ?? 0)}
                  />
                </Stack>
              </Stack>
            </AccordionDetails>
          </Accordion>

        </AccordionGroup>

        {/* ───────── DESIGN ───────── */}
        <Box sx={{ my: 3 }}>
          <Typography level="h4">Design</Typography>
          <ContentBox sx={{ p: 2 }}>
            <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
              <Button onClick={generateDesign} disabled={isGenerating || isUpdatingPreview}>
                <PlayCircleFilledWhiteIcon sx={{ mr: 1 }} />
                Generate Design
              </Button>

              {(isGenerating || isUpdatingPreview) && (
                <Stack direction="row" spacing={1} alignItems="center">
                  <CircularProgress size="sm" />
                  <Typography level="body-sm">
                    {isGenerating ? "Generating…" : "Updating preview…"}
                  </Typography>
                </Stack>
              )}

              <FormControl orientation="horizontal" sx={{ gap: 1, alignItems: "center" }}>
                <FormLabel>Color by flow rate</FormLabel>
                <Switch
                  checked={colorByFlow}
                  onChange={(event) => updatePreview((event.target as HTMLInputElement).checked)}
                  disabled={isGenerating || isUpdatingPreview}
                />
              </FormControl>
            </Stack>

            {output.dxfFiles && output.dxfFiles.length > 0 && (
              <Stack direction="row" spacing={2} alignItems="center" sx={{ mt: 2 }}>
                <FormControl sx={{ minWidth: 320 }}>
                  <FormLabel>DXF file</FormLabel>
                  <Select
                    value={selectedDxfUrl}
                    onChange={(_, v) => setSelectedDxfUrl(v ?? null)}
                    disabled={isGenerating}
                  >
                    {output.dxfFiles.map(f => (
                      <Option key={f.url} value={f.url}>
                        {f.name}
                      </Option>
                    ))}
                  </Select>
                </FormControl>

                <Button
                  component="a"
                  href={selectedDxfUrl ?? output.resultFile}
                  download
                  disabled={!selectedDxfUrl && !output.resultFile}
                  startDecorator={<OutputIcon />}
                  sx={{ alignSelf: "end" }}
                >
                  Download
                </Button>
              </Stack>
            )}

            {output.previewUrl && (
              <Stack direction="row" spacing={2} sx={{ mt: 2, alignItems: "flex-start", flexWrap: "wrap" }}>
                <Box sx={{ flex: 1, minWidth: 280 }}>
                  <img
                    src={`${output.previewUrl}?v=${nonce}`}
                    alt="Design Preview"
                    style={{
                      maxWidth: "100%",
                      border: `1px solid ${theme.vars.palette.divider}`,
                      borderRadius: theme.vars.radius.sm,
                    }}
                  />
                </Box>

                <Box
                  sx={{
                    minWidth: 240,
                    border: `1px solid ${theme.vars.palette.divider}`,
                    borderRadius: theme.vars.radius.sm,
                    backgroundColor: theme.vars.palette.background.surface,
                    p: 1.5,
                  }}
                >
                  <Stack spacing={1}>
                    <Stack direction="row" spacing={1.25} sx={{ alignItems: "center" }}>
                      <Box
                        sx={{
                          width: 14,
                          height: 14,
                          borderRadius: theme.vars.radius.xs,
                          backgroundColor: theme.vars.palette.danger[300],
                          border: `1px solid ${theme.vars.palette.divider}`,
                        }}
                      />
                      <Typography level="body-sm">Exclusion Zone</Typography>
                    </Stack>

                    <Stack direction="row" spacing={1.25} sx={{ alignItems: "center" }}>
                      <Box
                        sx={{
                          width: 14,
                          height: 14,
                          borderRadius: theme.vars.radius.xs,
                          backgroundColor: theme.vars.palette.success[300],
                          border: `1px solid ${theme.vars.palette.divider}`,
                        }}
                      />
                      <Typography level="body-sm">Mixing Module</Typography>
                    </Stack>

                    <Stack direction="row" spacing={1.25} sx={{ alignItems: "center" }}>
                      <Box
                        sx={{
                          width: 14,
                          height: 14,
                          borderRadius: theme.vars.radius.xs,
                          backgroundColor: theme.vars.palette.neutral[400],
                          border: `1px solid ${theme.vars.palette.divider}`,
                        }}
                      />
                      <Typography level="body-sm">Organ Module</Typography>
                    </Stack>
                  </Stack>
                </Box>
              </Stack>
            )}

            {output.error && (
              <Typography
                color="danger"
                startDecorator={<InfoOutlined />}
                sx={{ mt: 2 }}
              >
                {output.error}
              </Typography>
            )}
          </ContentBox>
        </Box>
        </Box>
      </main>

      {/* ───────── FOOTER ───────── */}
    <footer
      style={{
        backgroundColor: theme.vars.palette.primary[500],
        marginTop: "auto"
      }}
    >
      <a
        href="https://www.cda.cit.tum.de/research/microfluidics/"
        style={{     
          textDecoration: "none",
          width: "100%",
          maxWidth: "1280px",
          margin: "0 auto",
          display: "flex",
          justifyContent: "center"  
        }}
      >
        <Typography
          level="h4"
          sx={{
            color: theme.vars.palette.common.white,
            paddingY: 1
          }}
        >
          Chair for Design Automation<br />
          Technical University of Munich
        </Typography>
      </a>
    </footer>
    </div>
  )
}
