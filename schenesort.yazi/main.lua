-- Schenesort Yazi Plugin
-- Displays XMP metadata from sidecar files alongside image previews

local M = {}

-- Check if a file exists
local function file_exists(path)
    local f = io.open(path, "r")
    if f then
        f:close()
        return true
    end
    return false
end

-- Get XMP sidecar path for an image
local function get_xmp_path(image_path)
    return image_path .. ".xmp"
end

-- Parse XMP metadata using exiftool
local function parse_xmp(xmp_path)
    local metadata = {}

    -- Use exiftool with schenesort namespace config if available
    local config_path = os.getenv("HOME") .. "/.config/ExifTool/schenesort.config"
    local config_arg = ""
    if file_exists(config_path) then
        config_arg = "-config " .. config_path .. " "
    end

    -- Run exiftool to extract metadata
    local cmd = "exiftool " .. config_arg .. "-s -s -s "
        .. "-XMP:Description "
        .. "-XMP-schenesort:Scene "
        .. "-XMP-dc:Subject "
        .. "-XMP-schenesort:Mood "
        .. "-XMP-schenesort:Style "
        .. "-XMP-schenesort:Colors "
        .. "-XMP-schenesort:TimeOfDay "
        .. "-XMP-schenesort:Subject "
        .. "-XMP-schenesort:AiModel "
        .. "-XMP-schenesort:Width "
        .. "-XMP-schenesort:Height "
        .. "-XMP-schenesort:RecommendedScreen "
        .. "'" .. xmp_path .. "' 2>/dev/null"

    local handle = io.popen(cmd)
    if not handle then
        return metadata
    end

    local output = handle:read("*a")
    handle:close()

    -- Parse the output (one value per line in order)
    local lines = {}
    for line in output:gmatch("[^\r\n]+") do
        table.insert(lines, line)
    end

    -- Map to fields (order matches exiftool arguments)
    local fields = {
        "description", "scene", "tags", "mood", "style", "colors",
        "time_of_day", "subject", "ai_model", "width", "height", "recommended_screen"
    }
    for i, field in ipairs(fields) do
        if lines[i] and lines[i] ~= "" then
            metadata[field] = lines[i]
        end
    end

    return metadata
end

-- Format metadata for display
local function format_metadata(metadata)
    local lines = {}

    if metadata.description then
        table.insert(lines, { " Description ", "magenta" })
        table.insert(lines, { metadata.description, "white" })
        table.insert(lines, { "", "" })
    end

    if metadata.scene then
        table.insert(lines, { " Scene ", "magenta" })
        table.insert(lines, { metadata.scene, "gray" })
        table.insert(lines, { "", "" })
    end

    if metadata.tags then
        table.insert(lines, { " Tags ", "cyan" })
        table.insert(lines, { metadata.tags, "cyan" })
        table.insert(lines, { "", "" })
    end

    if metadata.mood then
        table.insert(lines, { " Mood ", "yellow" })
        table.insert(lines, { metadata.mood, "yellow" })
        table.insert(lines, { "", "" })
    end

    if metadata.style then
        table.insert(lines, { " Style ", "green" })
        table.insert(lines, { metadata.style, "green" })
        table.insert(lines, { "", "" })
    end

    if metadata.colors then
        table.insert(lines, { " Colors ", "blue" })
        table.insert(lines, { metadata.colors, "blue" })
        table.insert(lines, { "", "" })
    end

    if metadata.time_of_day then
        table.insert(lines, { " Time ", "white" })
        table.insert(lines, { metadata.time_of_day, "white" })
        table.insert(lines, { "", "" })
    end

    if metadata.subject then
        table.insert(lines, { " Subject ", "white" })
        table.insert(lines, { metadata.subject, "white" })
        table.insert(lines, { "", "" })
    end

    if metadata.width and metadata.height then
        table.insert(lines, { " Size ", "cyan" })
        table.insert(lines, { metadata.width .. " x " .. metadata.height, "white" })
        if metadata.recommended_screen then
            table.insert(lines, { "Best for: " .. metadata.recommended_screen, "green" })
        end
        table.insert(lines, { "", "" })
    end

    if metadata.ai_model then
        table.insert(lines, { " AI Model ", "gray" })
        table.insert(lines, { metadata.ai_model, "gray" })
    end

    return lines
end

-- Main peek function - called by Yazi to render preview
function M:peek(job)
    local path = tostring(job.file.url)
    local xmp_path = get_xmp_path(path)

    -- Check if XMP sidecar exists
    if not file_exists(xmp_path) then
        -- No sidecar, fall back to built-in image preview
        return require("image"):peek(job)
    end

    -- Parse metadata
    local metadata = parse_xmp(xmp_path)

    -- If no metadata found, fall back to image preview
    if not next(metadata) then
        return require("image"):peek(job)
    end

    -- Calculate layout - image takes top 70%, metadata takes bottom 30%
    local area = job.area
    local image_height = math.floor(area.h * 0.7)
    local metadata_height = area.h - image_height - 1  -- -1 for separator

    -- Render image in top portion
    local image_area = ui.Rect {
        x = area.x,
        y = area.y,
        w = area.w,
        h = image_height,
    }

    -- Use Yazi's built-in image preview for the image portion
    local image_job = {
        file = job.file,
        area = image_area,
        skip = job.skip,
    }
    require("image"):peek(image_job)

    -- Render separator line
    local separator_y = area.y + image_height
    ya.preview_widgets(job, {
        ui.Bar(ui.Rect { x = area.x, y = separator_y, w = area.w, h = 1 })
            :symbol("─")
            :style(ui.Style():fg("darkgray")),
    })

    -- Render metadata in bottom portion
    local metadata_lines = format_metadata(metadata)
    local widgets = {}
    local y_offset = separator_y + 1

    for i, line_data in ipairs(metadata_lines) do
        if y_offset + math.floor((i - 1) / 2) >= area.y + area.h then
            break
        end

        local text, color = line_data[1], line_data[2]
        if text ~= "" then
            local style = ui.Style()
            if color == "magenta" then
                style = style:fg("magenta"):bold()
            elseif color == "cyan" then
                style = style:fg("cyan")
            elseif color == "yellow" then
                style = style:fg("yellow")
            elseif color == "green" then
                style = style:fg("green")
            elseif color == "blue" then
                style = style:fg("blue")
            elseif color == "gray" then
                style = style:fg("darkgray")
            else
                style = style:fg("white")
            end

            table.insert(widgets,
                ui.Line { ui.Span(text):style(style) }
                    :area(ui.Rect { x = area.x, y = y_offset, w = area.w, h = 1 })
            )
            y_offset = y_offset + 1
        end
    end

    ya.preview_widgets(job, widgets)
end

-- Seek function - handle scrolling
function M:seek(job)
    local path = tostring(job.file.url)
    local xmp_path = get_xmp_path(path)

    -- If no sidecar, delegate to image seek
    if not file_exists(xmp_path) then
        return require("image"):seek(job)
    end

    -- For now, just delegate to image seek
    -- Metadata panel doesn't scroll separately
    require("image"):seek(job)
end

-- Preload function - called before peek for caching
function M:preload(job)
    local path = tostring(job.file.url)
    local xmp_path = get_xmp_path(path)

    -- Preload image
    require("image"):preload(job)

    -- Optionally pre-parse XMP if it exists
    if file_exists(xmp_path) then
        -- Could cache metadata here in future
    end

    return 1  -- Success
end

return M
