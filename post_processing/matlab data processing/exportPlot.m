function exportPlot(width, height, basename)

    execTimeLabel = datestr(datetime("now"), 'yyyy-mm-dd_HH-MM-SS') + ".pdf";
    
    % Set renderer to painters for transparent background
    set(gcf, 'Renderer', 'painters');
    
    % Export the plot as a PNG with transparent background
    set(gcf, 'Position', [100, 100, width, height]);  % Set position and size
    
    filename = append('', basename + execTimeLabel);
    
    exportgraphics(gcf, filename, 'ContentType', 'Vector');

end