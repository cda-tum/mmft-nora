function plotROIs(ROIData, titles, dim)

    loadedData = load(ROIData); 
    ROIData = loadedData.ROIData;

    figure

    N = length(ROIData);
    plotIdx = 0;  % index for subplot position
    
    % For each image, plot the image with ROI
    for i = 1:N    
        % Find image from name
        name = titles{i,1};
        idx = find(contains({ROIData.image}, name));
        path = ROIData(idx).image;
    
        plotIdx = plotIdx + 1;
        img = imread(path);
        
        % Main box
        rect = ROIData(idx).roiBox; % [x y w h]
    
        % Ensure integer indices
        x = ceil(rect(1));
        y = ceil(rect(2));
        w = floor(rect(3));
        h = floor(rect(4));
    
        crop = img(y:y+h-1, x:x+w-1, :);

        % BG box
        rectbg = ROIData(idx).backgroundBox; % [x y w h]
    
        % Ensure integer indices
        x = ceil(rect(1));
        y = ceil(rect(2));
        w = floor(rect(3));
        h = floor(rect(4));
    
        crop = img(y:y+h-1, x:x+w-1, :);
    
        % --- Plot ---
        subplot(dim(1), dim(2), plotIdx);
        imshow(img);
        hold on;
        drawrectangle('Color', 'r', 'Position', rect);
        % drawrectangle('Color', 'b', 'Position', rectbg);
    
        [~, name, ~] = fileparts(path);
        if(isempty(titles))
            title(name, 'Interpreter', 'none'); % avoids underscore issues
        else
            name_title = titles{i,2};
            title(name_title, 'Interpreter', 'none'); % avoids underscore issues            
        end
        hold off;
    end


    %% Format plot
    
    % Add legend
    subplot(dim(1), dim(2),1)
    hold on;
    fill([NaN NaN NaN NaN], [NaN NaN NaN NaN], 'r', 'FaceAlpha', 0.3);
    legend('Region of Interest')
    
    % Header
    sgtitle("Dataset ROIs");    
end


