(function() {
    window.Hi = window.Hi || {};
    
    const HiSvgUtils = {
	overlayData: function( svgOverlayData ) {

	    const baseSvgData = getBaseSvgData( svgOverlayData.base_html_id );
	    
	}
    };
    
    window.Hi.svgUtils = HiSvgUtils;

    function getBaseSvgData( htmlId ) {

	const $baseSvg = $('#' + htmlId + ' svg' );

	const bbox = $baseSvg[0].getBoundingClientRect();

	const viewBox = $baseSvg.attr('viewBox').split(' ').map(Number);
	const viewBoxWidth = viewBox[2];
	const viewBoxHeight = viewBox[3];
	
	const scaleX = bbox.width / viewBoxWidth;
	const scaleY = bbox.height / viewBoxHeight;
	
	return {
	    htmlBoundingBox : bbox,
	    svgViewBox : { x: viewBox[0], y: viewBox[1], width: viewBox[2], height: viewBox[3] },
	    scaleX : scaleX,
	    scaleY : scaleY
	};
    }
    
})();
