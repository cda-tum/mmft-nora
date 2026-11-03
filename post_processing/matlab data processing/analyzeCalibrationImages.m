function calibrationData = analyzeCalibrationImages(ROIDataCalibration, ...
    backgroundMapping)
    % Script performing colorimetry on a series of calibration images,
    % generating a datastructure storing a calibration curve for use in
    % quantification of experimental data.
    % 
    % ROIData: path to 1XN struct output to annotateBackgroundAndROI with 
    % the images and regions to use in the analysis.
    %
    % backgroundMapping: Nx2 cell array pairing an image name and a
    % background name. 
    % 
    % CalibrationData: 1x2 cell array containing 
    %   X: the dilution factor for each image
    %   Y: the colour data for each image
    %
    
    %% Read and process colour data from images
    
    % load ROI data
    loadedData = load(ROIDataCalibration); 
    ROIData = loadedData.ROIData;

    % Initialize cell array to hold data for each image    
    names = {}; % file name - should to end in dilution factor (i.e. _10x)
    colours = {}; 
    bgcolours = {};
    
    % Loop over every image    
    for i = 1:length(ROIData)

        % Load image
        path = ROIData(i).image;
        img = imread(path);
        
        % Load ROI
        rect = ROIData(i).roiBox; % [x y w h]
        
        % Crop ROI from image
        x = ceil(rect(1));
        y = ceil(rect(2));
        w = floor(rect(3));
        h = floor(rect(4));
        crop = img(y:min(y+h, size(img,1)),x:min(x+w, size(img, 2)), :);
    
        % Blur ROI
        crop = imgaussfilt(crop, 20);
        
        % Average colour and reshape matrix
        colour = squeeze(mean(mean(crop, 1), 2));
    
        % Load background region
        rect = ROIData(i).backgroundBox; % [x y w h]

        % Crop ROI from image
        x = ceil(rect(1));
        y = ceil(rect(2));
        w = floor(rect(3));
        h = floor(rect(4));
        crop = img(y:min(y+h, size(img,1)),x:min(x+w, size(img, 2)), :);

        % Blur ROI
        crop = imgaussfilt(crop, 20);
    
        % Average colour and reshape matrix
        bgcolour = squeeze(mean(mean(crop, 1), 2));
    
        % Store data for this image
        [filepath,name,ext] = fileparts(path);
        names = [names name];
        colours = [colours colour];
        bgcolours = [bgcolours bgcolour];
    
    end
    
    % Create mapping name -> colours 
    colourmap = containers.Map(names, colours);
    bgcolourmap = containers.Map(names, bgcolours);
    

    %% Make and plot calibration curve

    % Call function to compile calibration curve data
    [X, Y] = analyzeCalibration(colourmap, bgcolourmap, ...
        backgroundMapping);

    %% Format plot

    % Create figure and plot calibration data
    figure
    plotCalibration(X, Y);
    title("RGB and Saturation in Chip")

    % Store calibration data
    calibrationData = cell(1,2);
    calibrationData(1,1) = {X};
    calibrationData(1,2) = {Y};

    % Add legend
    legend("RGB Value", "Saturation")
    
    %% Analyze calibration data

    function [X, Y] = analyzeCalibration(colourmap, bgcolourmap, backgroundMapping)
        % Compile the calibration colour data, calculating colour derived 
        % metrics
        %
        % colourmap: mapping name -> colour
        % bgcolourmap: mapping name -> background colour
        % backgroundMapping: Nx2 cell array pairing an image name and a
        %   background name. 
        %
        % X: the dilution factor for each calibration point
        % Y: the colour data for each calibration point (R, G, B, sat)
        %    
    
        N = size(backgroundMapping,1);
        X = zeros(N, 1);
        Y = zeros(N, 4);
        
        for i = 1:N
            % Extract dilution factor from name
            name = backgroundMapping{i,1};
            % ^\d+(?=x) matches digits before 'x'
            Xstr = regexp(name, '\d+(?=x)', 'match');  
            Xnum = cellfun(@str2double, Xstr);
            Xstr = [Xstr{1} 'x'];
            if(isempty(Xnum) || isnan(Xnum))
               Xnum = 10e3; % Assume finite maximum dilution
            end
            X(i) = Xnum;
    
            % Calculate brightness and saturation for calibration image
            colour = colourmap(name);
            br = max(colour);
            sat = (max(colour) - min(colour))/max(colour); 
            
            % Calculate brightness and saturation for background image
            bgname = backgroundMapping{i,2};
            bgcolour = colourmap(bgname);
            bgbr = max(bgcolour);
            bgsat = (max(bgcolour) - min(bgcolour))/max(bgcolour);          
        

            % This formula can be adjusted using the variables above
            % to perform background compensation etc.
            compColour = colour; 

            % Store analysis data
            Y(i,1) = compColour(1);
            Y(i,2) = compColour(2);
            Y(i,3) = compColour(3);
            Y(i,4) = (max(compColour) - min(compColour))/max(compColour)*100;

        end
    end

    %% Plot calibration data
    function plotCalibration(X, Y)
        % Plot the calibration data
        % X: the dilution factor for each calibration point
        % Y: the colour data for each calibration point (R, G, B, sat)
        % backgroundMapping: Nx2 cell array pairing an image name and a
        %   background name. 

        % load colours for plotting
        defaultcolours = get(groot,"FactoryAxesColorOrder");
    
        % Loop over all dilutions
        N = size(X,1);
        
        for i = 1:N
            Xnum = X(i);
            Xstr = [num2str(X(i)) 'x'];
    
            % Plot labels with R value and saturation for this dilution
            yyaxis left    
            text(X(i), Y(i,1), Xstr, 'VerticalAlignment', 'bottom', 'HorizontalAlignment', 'right', 'Color', defaultcolours(1,:));
            yyaxis right    
            text(X(i), Y(i,4), Xstr, 'VerticalAlignment', 'bottom', 'HorizontalAlignment', 'right', 'Color', defaultcolours(2,:));
        end
        
        hold on;
    
        % Plot R values
        yyaxis left
        ylabel('RGB value (0-255)')        
        plot(X(1:end),Y(1:end,1),'ko-', 'Color', defaultcolours(1,:));
        ylim([0 255])

        % Plot Saturation values
        yyaxis right    
        ylabel('Saturation (%)')
        plot(X(1:end),Y(1:end,4),'ko-', 'Color', defaultcolours(2,:));

        % format X axis
        xlabel('Dilution Factor')
    end
end
