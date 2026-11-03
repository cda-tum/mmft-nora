function analyzeExperimentImages(calibrationData, ROIDataExperiment, backgroundMapping)
    % Script performing colorimetry on a series of experimental images 
    % using the data from colorimetry on a series of calibration images
    % to plot a comparison between the two.
    % 
    % calibrationData: 1x2 cell array containing 
    %   X: the dilution factor for each image
    %   Y: the colour data for each image
    % ROIDataExperiment: path to 1xN struct output to 
    %   annotateBackgroundAndROI with the experimental images and regions 
    %   to use in the analysis.
    % backgroundMapping: Nx2 cell array pairing an image name and a
    %   background name. 
    %
    
    %% Read and process colour data from images
    
    % load ROI data
    loadedData = load(ROIDataExperiment); 
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


    %% Analyze experiment colour
    
    % Analyze experimental data
    [Xexp, Yexp] = analyzeExperiment(colourmap, bgcolourmap, backgroundMapping);

    % load calibration data
    Xcalib = calibrationData{1};
    Ycalib = calibrationData{2};

    %% Plot comparison between experimental data and calibration data
    
    % Open figure
    figure;
    
    % Define colours for use in plotting
    experimentColors = {'#153460', '#5c99a2', '#929d95'}; 
    calibrationColor = [0.8,0.4,0.0];
    
    % Draw the ideal identity line where experimental and calibration would
    % be equal
    limits = [0 100];
    plot(limits, limits, 'k--', 'LineWidth', 1, 'Color', calibrationColor, 'HandleVisibility', 'off');
    
    % format plot
    hold on;
    fontsize(14,"points")
        
    % plot calibration data
    plot(Ycalib(:,4), Ycalib(:,4), 'o', ... % saturation
        'MarkerEdgeColor', calibrationColor, ...
        'MarkerFaceColor', calibrationColor);
    
    % Annotate data
    textIdx = ~ismember(Xcalib, Xexp); % calibration indices corresponding to experiment
    text(Ycalib(textIdx,4)+1, Ycalib(textIdx,4)-1, string(Xcalib(textIdx)) + "x", ...
        'Color', 1-0.3*(1-calibrationColor), ...
         'FontSize', 12, ...
        'HorizontalAlignment', 'left', ...
        'VerticalAlignment', 'middle', ...
        'FontWeight', 'bold');
    
    % plot experimental data
    plotExperiment(Xcalib, Ycalib, Xexp, Yexp, experimentColors)

    %% Format plot

    ax = gca;
    ax.FontWeight = 'normal';
    ax.FontSize = 12;
    ax.LineWidth  = 0.5;
    box off;
    ax.XMinorGrid = 'off';
    ax.YMinorGrid = 'off';
    
    xlabel('Calibration Saturation (%)');
    ylabel('Experimental Saturation (%)');
    title('Comparison between Experimental and Calibration Saturation');
    
    % Square the axes for 1:1 visual comparison
    axis equal;
    xlim(limits);
    ylim(limits);
    
    hold off;    
    
    %% Analyze experimental data
    
    function [X, Y] = analyzeExperiment(colourmap, bgcolourmap, backgroundMapping)
        % Compile the experiment colour data, calculating colour derived 
        % metrics
        %
        % colourmap: mapping name -> colour
        % bgcolourmap: mapping name -> background colour
        % backgroundMapping: Nx2 cell array pairing an image name and a
        %   background name. 
        %
    
        N = size(backgroundMapping,1);
        X = zeros(N, 1);
        Y = zeros(N, 4);
        
        for i = 1:N
            % Extract target dilution factor from name
            name = backgroundMapping{i,1};
            % ^\d+(?=x) matches digits before 'x'
            Xstr = regexp(name, '\d+(?=x)', 'match'); 
            Xnum = cellfun(@str2double, Xstr);
            if(isempty(Xnum) || isnan(Xnum))
                Xnum = inf; % Assume water
            end
            X(i) = Xnum;
    
            %% Analyze experimental colours

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

    %% Plot experimental data against calibration data
    
    function plotExperiment(Xcalib, Ycalib, Xexp, Yexp, colors)
    
        % Plot the experimental data against the calibraiton data
        % X: the dilution factor for each experiment point
        % Y: the colour data for each experiment point (R, G, B, sat)
        % colors: color to use when plotting each experiment point
        %
    
        N = size(Xexp,1);
        
        for i = 1:N
            Xnum = Xexp(i);
            Xstr = [num2str(Xnum) 'x'];

            %% Load calibration saturation
            idx = find(Xcalib == Xnum);
            if(isempty(idx))
                % We skip this. We could interpolate our calibration, but
                % our calibration was designed to include our target
                % dilution factors
                continue;
            end

            % We compare the saturation
            calibrationSat = Ycalib(idx(1),4);
            experimentSat = Yexp(i,4);

            % plot marker at calibration point
            plot(calibrationSat, experimentSat, 'o', ... % sat
                'MarkerEdgeColor', colors{i}, ...
                'MarkerFaceColor', colors{i});
            
            % Add text annotation
            text(calibrationSat, experimentSat+5, [num2str(Xnum) 'x'], ...
                'HorizontalAlignment', 'center', ...
                'VerticalAlignment', 'middle', ...
                'FontSize', 12, ...
                'FontWeight', 'bold');
    
            % plot residual error
            plot([calibrationSat, calibrationSat], [calibrationSat experimentSat], ...
                'Color', colors{i}, 'LineWidth',2);
            
            % Annotate residual error: {\\boldmath$\\alpha=%d$}
            text(calibrationSat + 2, calibrationSat + (experimentSat - calibrationSat)*0, ['{\boldmath$e=' num2str(experimentSat - calibrationSat, 2) '$}'], ...
                'Interpreter', 'latex', ...
                'HorizontalAlignment', 'left', ...
                'VerticalAlignment', 'middle', ...
                'FontSize', 10, ...
                'FontWeight', 'bold', ...
                'Color', colors{i});
        end    
    end
end