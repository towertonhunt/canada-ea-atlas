var olConfig = {
    api: 'exploration/api-map',
    wms: 'https://geoappext.nrcan.gc.ca/arcgis/rest/services/BaseMaps/CBMT_CBCT_GEOM_3857/MapServer/tile/{z}/{y}/{x}', // OR -> new ol.source.OSM(),
    mapElement: 'ol-geomap',
    layers: [
        {
            source: 'IAAC-AEIC',
            url: ('/050/evaluations/proj'),
            id: 'file_number',
            icon: '/050/evaluations/Content/images/ceaa_tear_p3_blue.png',
            el: '#CEAA-ACEE_loader'
        }
    ]
};