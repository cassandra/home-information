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
	const viewBox = Hi.getSvgViewBox( $baseSvg );	

	const scaleX = bbox.width / viewBox.width;
	const scaleY = bbox.height / viewBox.height;
	
	return {
	    htmlBoundingBox : bbox,
	    svgViewBox : viewBox,
	    scaleX : scaleX,
	    scaleY : scaleY
	};
    }
    
})();
