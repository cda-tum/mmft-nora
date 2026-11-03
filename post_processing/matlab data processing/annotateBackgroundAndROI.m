function ROIData = annotateBackgroundAndROI(imagePaths)
    % Function that opens a GUI where the user can position boxes
    % indicating a ROI and a Background Region. A struct is generated
    % storing the figures together with the ROIs
    % 
    % imagePaths: A 1xN cell array containing string paths to the images 
    % to be processed
    %
    % results: A 1xN struct with for each image the image path, background
    % region data and ROI data.
    %

    % Create UIFigure
    fig = uifigure('Name', 'Box drawing tool', 'Position', [100, 100, 1200, 600]);

    % Specify Layout
    mainGrid = uigridlayout(fig, [1, 2]);
    mainGrid.ColumnWidth = {'6x', '1x'};

    % Create axes to display image
    imgAx = uiaxes(mainGrid);
    hold(imgAx, 'on');
    axis(imgAx, 'image');
    imgAx.XTick = [];
    imgAx.YTick = [];
    imgAx.XColor = 'none';
    imgAx.YColor = 'none';

    % Add control panel for accept button
    controlPanel = uipanel(mainGrid, 'Title', 'Controls');
    controlGrid = uigridlayout(controlPanel, [2, 1]);
    controlGrid.RowHeight = {'1x', '8x'};

    % Output struct
    ROIData = struct('image', [], 'backgroundBox', [], 'roiBox', []);

    % ROI handles (persist between images)
    hBg = [];
    hRoi = [];
    acceptButton = [];

    % Display first image
    img = imread(imagePaths{1});
    hImg = imshow(img, 'Parent', imgAx);

    % Loop over all images
    numImages = length(imagePaths);

    for i = 1:numImages

        % Load and display image
        img = imread(imagePaths{i});
        set(hImg, 'CData', img);
        title(imgAx, ['Image ', num2str(i), ': Draw/Adjust boxes, then press Accept']);

        % Initialize boxes for first image
        if i == 1
            % Draw background region box (red)
            hBg = drawrectangle(imgAx, 'Color', 'r');
            addlistener(hBg, 'ROIMoved', @(~,~) updateLabel(hBg, 'background'));
            updateLabel(hBg, 'background');

            % Draw ROI box (blue)
            hRoi = drawrectangle(imgAx, 'Color', 'b');
            addlistener(hRoi, 'ROIMoved', @(~,~) updateLabel(hRoi, 'ROI'));
            updateLabel(hRoi, 'ROI');
            
            % Create Accept button
            acceptButton = uibutton(controlGrid, ...
                'Text', 'Accept', ...
                'ButtonPushedFcn', @acceptCallback);

        else
            % For other boxes, re-parent to new axes

            % Keep same objects, just re-parent to new axes
            hBg.Parent = imgAx;
            hRoi.Parent = imgAx;
        end

        % Update labels immediately
        updateLabel(hBg, 'background');
        updateLabel(hRoi, 'ROI');

        % Wait for user to adjust boxes. the accept button callback will
        % resume operation
        uiwait(fig);

        % Store data and annotation
        ROIData(i).image = imagePaths{i};
        ROIData(i).backgroundBox = hBg.Position;
        ROIData(i).roiBox = hRoi.Position;

    end

    %% Save results
    saveFileName = "output/ROIData_" + datestr(datetime("now"), 'yyyy-mm-dd_HH-MM-SS') + ".mat";
    save(saveFileName, "ROIData");

    disp("All images processed. Data saved as " + saveFileName);

    close(fig);

    %% Callbacks
    function acceptCallback(~, ~)
        % Pause program until the UI button is pressed

        uiresume(fig);
    end

    function updateLabel(hRect, labelText)
        % Place text label near an ROI rectangle

        pos = hRect.Position;

        % Delete existing label if any
        if isfield(hRect.UserData, 'label') && isvalid(hRect.UserData.label)
            delete(hRect.UserData.label);
        end

        % Create text label
        hRect.UserData.label = text(imgAx, ...
            pos(1)+20, pos(2)+30, ...
            labelText, ...
            'Color', hRect.Color, ...
            'FontWeight', 'bold', ...
            'FontSize', 12);
    end

end