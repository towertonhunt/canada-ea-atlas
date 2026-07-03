var initialMapLoad = true;
var olHelpers = (typeof (ol) !== 'undefined') ? {

    inOverlay: false,

    createLayer: function (search, facets, layerConfig, onFeaturesLoaded) {
        if (search != null && search.length > 0)
            initialMapLoad = false;

        var format = new ol.format.GeoJSON();

        var vectorSource = new ol.source.Vector({
            format: format,
            loader: function (extent, resolution, projection) {
                $.post(olConfig.api, {
                    search: search,
                    facets: facets,
                    source: layerConfig.source,
                    dateFilter: dateRange,
                    projectID: projectID,
                    useMap: mapEnabled,
                    projectDocuments: projectDocuments,
                    activeProjects: activeProjects,
                    inactiveProjects: inactiveProjects,
                    mostRecent: mostRecent
                }).then(function (response) {

                    try {

                        var jsonResponse = JSON.parse(response);

                        if (jsonResponse && jsonResponse.features.length > 0) {
                            var features = format.readFeatures(jsonResponse, {
                                featureProjection: 'EPSG:3857'
                            });

                            vectorSource.addFeatures(features);
                        }

                    } catch (ex) {
                        console.error(ex)
                    } finally {
                        onFeaturesLoaded(vectorSource);
                    }
                });
            }
        });

        var style = new ol.style.Style({
            image: new ol.style.Icon({
                scale: 1.0, // http://www.iconarchive.com/tag/map,
                src: layerConfig.icon,
                anchor: [0.5, 1.0]
            })
        });
        //NEWER CLUSTER SOURCE FOR MULTIPOINT - DISPLAYS ONLY A SINGLE POINT PER PROJECT
        //var clusterSource = new ol.source.Cluster({
        //    source: vectorSource,
        //    geometryFunction: function (feature) {
        //        var geom = feature.getGeometry();
        //        if (geom.getType() == 'Point') {
        //            //console.log('Point', geom);
        //            return geom;
        //        } else if (geom.getType() == 'MultiPoint') {
        //            //console.log('MultiPoint', geom.getPoint(0));
        //            return geom.getPoint(0);
        //        } else if (geom.getType() == 'Polygon') {
        //            //console.log('Polygon', geom.getInteriorPoint());
        //            return geom.getInteriorPoint();
        //        } else if (geom.getType() == 'LineString') {
        //            let linePoint = new ol.geom.Point(geom.getLastCoordinate());
        //            //console.log('LineString', linePoint);
        //            return linePoint;
        //        }
        //        return null;
        //    },
        //    distance: 10
        //});

        //OLD CLUSTER SOURCE
        //var clusterSource = new ol.source.Cluster({
        //    source: vectorSource,
        //    distance: 10
        //});

        return new ol.layer.Vector({
            //source: clusterSource,
            source: vectorSource,
            style: style
        });
    },

    createMap: function (config, layers) {

        var map = new ol.Map({
            // Improve user experience by loading tiles while animating. Will make
            // animations stutter on mobile or slow devices.
            loadTilesWhileAnimating: true,
            controls: [
                new ol.control.ScaleLine(),
                new ol.control.FullScreen({
                    tipLabel: DecodeHtml(Resources.lblMapControl_FullScreen)
                }),
                new ol.control.Attribution({
                    collapsed: false,
                    collapsible: false
                }),
                new ol.control.Zoom({
                    zoomInTipLabel: Resources.lblMapControl_ZoomIn,
                    zoomOutTipLabel: DecodeHtml(Resources.lblMapControl_ZoomOut),
                }),
                new ol.control.ZoomToExtent({
                    label: "⌂",
                    tipLabel: (document.documentElement.lang === "fr" ? "Réinitialization de la vue" : "Reset View"),
                    extent: [-14886644.184293684, 5206024.461292353, -5120696.576490585, 10892116.02759210]
                })
            ],
            layers: [
                new ol.layer.Tile({
                    source: (typeof (config.wms) === 'string')
                        ? new ol.source.XYZ({
                            attributions: [DecodeHtml(Resources.NRCanBasemapAttributionURL)],
                            url: config.wms
                        })
                        : config.wms
                }),
                new ol.layer.Tile({
                    source: new ol.source.XYZ({
                        url: Resources.NRCanBasemapLabelsURL
                    })
                })
            ].concat(layers),
            target: config.mapElement,
            view: new ol.View({
                center: ol.proj.transform([-94.83480853299199, 54.68694931990032], 'EPSG:4326', 'EPSG:3857'),
                minZoom: 2.0,
                maxZoom: 12.0,
                zoom: 3.0,
                multiWorld: false,
                extent: ol.proj.transformExtent([-180, 90, 180, -90], 'EPSG:4326', 'EPSG:3857')
            })
        });

        $('#' + config.mapElement).data('map', map);

        var container = document.getElementById('popup');

        //Add a click handler to hide the popup.
        var closer = $('#popup-closer');
        closer.click(function () {
            popup.setPosition(undefined);
            closer.blur();
        });

        popup = new ol.Overlay({
            element: container,
            stopEvent: true,
            offset: [1, 0],
            autoPan: true,
            autoPanAnimation: {
                duration: 100
            }
        });

        map.addOverlay(popup);

        map.on('click', function (event) {
            if (!map.hasFeatureAtPixel(event.pixel)) {
                popup.setPosition(undefined);
            } else {
                map.forEachFeatureAtPixel(event.pixel, function (feature) {
                    if ($('html').is('.smallview, .xsmallview, .xxsmallview')) {
                        olHelpers.popup(feature, config, event);
                    } else {
                        olHelpers.click(feature, config);
                    }
                });
            }
        });

        map.on('dblclick', function (event) {
            if (!map.hasFeatureAtPixel(event.pixel)) {
                popup.setPosition(undefined);
            } else {
                map.forEachFeatureAtPixel(event.pixel, function (feature) {
                    olHelpers.click(feature, config);
                });
            }
        });

        var isOnPopupContent = false;
        $('#popupContent').mouseenter(function () { isOnPopupContent = true; });
        $('#popupContent').mouseleave(function () { isOnPopupContent = false; });

        map.on('pointermove', function (event) {
            if (popup.getPosition() !== undefined && isOnPopupContent) {
                return;
            }
            if (map.hasFeatureAtPixel(event.pixel)) {
                var features = map.getFeaturesAtPixel(event.pixel);
                if (features.length == 1) {
                    if ($('html').not('.smallview, .xsmallview, .xxsmallview')) {
                        popup.setPosition(undefined);
                        olHelpers.popup(features, config, event);
                    }
                }
                else if (features.length >= 2) {
                    if ($('html').not('.smallview, .xsmallview, .xxsmallview')) {
                        popup.setPosition(undefined);
                        olHelpers.popup(features, config, event);
                    }
                }
            }
            //map.forEachFeatureAtPixel(event.pixel, function (feature) {
            //    if ($('html').not('.smallview, .xsmallview, .xxsmallview')) {
            //        popup.setPosition(undefined);
            //        olHelpers.popup(feature, config, event);
            //    }
            //});
        });

        return map;
    },
    popup: function (features, config, event) {

        var cnt = features.length;
        //var coordinates = feature.getGeometry().getCoordinates();
        var content = document.getElementById('popupContent');
        var popupContent = '<p style="padding: 5px; margin: 10px;">' + Resources.ThereAre + cnt + Resources.ProjectsAtThisLocation + '</p>'
        //var props = feature.getProperties().features[0];

        if (cnt > 10) {

            content.innerHTML = popupContent;

        } else if (cnt > 1) {

            title = Resources.PopupHeader + 's';

            popupContent = '<table class="map-popup map-table" style="width: 100%; white-space: normal;">';
            popupContent += '<tr style="vertical-align: top;"> <thead style="background: rgba(0,60,136,.6); color: #fff;"> <th style=""><strong>' + title + '</strong></th></thead>';

            popupContent += '<tr style="vertical-align: top;"><td style=""><ul style="padding-left: 20px; padding-right: 5px;">';

            var sources = [];

            $(config.layers).each(function (idx, layer) {
                sources[layer.source.toLowerCase()] = {
                    id: layer.id,
                    url: layer.url
                }
            });

            var fileLanguage = "details-eng";
            if (document.documentElement.lang == 'fr')
                fileLanguage = "details-fra";

            $.each(features, function item(idx, item) {

                var source = item.get('source').toLowerCase();
                var id = item.get('project_id').toLowerCase();

                var url = sources[source].url + '/' + id;
                if (item.get('document_type').includes('archive')) {
                    url = 'https://iaac-aeic.gc.ca/archives/evaluations' + item.get('relative_path')
                    var filename = item.get('file_name').toString();

                    if (filename.includes(fileLanguage)) {
                        popupContent += '<li style=""><a href="' + url + '" style="">' + item.get('project_name_' + document.documentElement.lang) + '</a></li>';
                    }
                }
                else {
                    popupContent += '<li style=""><a href="' + url + '" style="">' + item.get('project_name_' + document.documentElement.lang) + '</a></li>';
                }
            });

            popupContent += '</ul></td></tr>';
            popupContent += '</table>';
            content.innerHTML = popupContent;


        } else if (cnt == 1) {

            title = Resources.PopupHeader;

            popupContent = '<table class="map-popup map-table" style="width: 100%; white-space: normal;">';
            popupContent += '<tr style="vertical-align: top;"> <thead style="background: rgba(0,60,136,.5);color: #fff;"> <th style=""><strong>' + title + '</strong></th></thead>';

            popupContent += '<tr style="vertical-align: top;"><td style=""><ul style="padding-left: 20px; padding-right: 5px;">';

            var sources = [];

            $(config.layers).each(function (idx, layer) {
                sources[layer.source.toLowerCase()] = {
                    id: layer.id,
                    url: layer.url
                }
            });

            var props = features[0];
            var source = props.get('source').toLowerCase();
            var url = sources[source].url;
            var id = props.get('project_id').toLowerCase();

            if (props.get('document_type').toLowerCase().includes('archive'))
            {
                url = 'https://iaac-aeic.gc.ca/archives/evaluations' + props.get('relative_path')
                var filename = props.get('file_name').toString();
                    popupContent += '<li style=""><a href="' + url + '" style="">' + props.get('project_name_' + document.documentElement.lang) + '</a></li>';
                
            }
            else {
                popupContent += '<li style=""><a href="' + url + '/' + id + '" style="">' + props.get('project_name_' + document.documentElement.lang) + '</a></li>';
            }

    
            popupContent += '</ul></td></tr>';
            popupContent += '</table>';
            content.innerHTML = popupContent;

        }

        //Attempting to stop the popup from running out of the map area
        //var mapSize = $('#' + config.mapElement).data('map').getSize();
        //var popupDeadzoneX = 280;
        //var popupDeadzoneY = 74;
        //var placement = "right";
        //if (mapSize[1] - event.pixel[1] < popupDeadzoneY) {
        //    placement = "top";
        //    popup.setOffset([0, -25]);
        //}
        //else if (mapSize[0] - event.pixel[0] < popupDeadzoneX) {
        //    placement = "left";
        //    popup.setOffset([-10, -10]);
        //}
        //else {
        //    popup.setOffset([0, -10]);
        //}

        //popup.setPlacement(placement);
        popup.setPosition(event.coordinate);
    },

    //popup: function (feature, config, event) {
         
    //    var cnt = 1;//feature.getProperties().features.length;
    //    //var coordinates = feature.getGeometry().getCoordinates();
    //    var content = document.getElementById('popupContent');
    //    var popupContent = '<p style="padding: 5px; margin: 5px;">' + Resources.ThereAre + cnt + Resources.ProjectsAtThisLocation + '</p>'
    //    //var props = feature.getProperties().features[0];

    //    if (cnt > 10) {

    //        content.innerHTML = popupContent;

    //    } else if (cnt > 1) {

    //        title = Resources.project + 's';
           
    //        popupContent = '<table class="map-popup map-table" style="width: 100%; white-space: normal;">';
    //        popupContent += '<tr style="vertical-align: top;"> <thead style="background: rgba(0,60,136,.6); color: #fff;"> <th style=""><strong>'+title+'</strong></th></thead>';

    //        popupContent += '<tr style="vertical-align: top;"><td style=""><ul style="padding-left: 20px; padding-right: 5px;">';

    //        var sources = [];

    //        $(config.layers).each(function (idx, layer) {
    //            sources[layer.source.toLowerCase()] = {
    //                id: layer.id,
    //                url: layer.url
    //            }
    //        });

    //        $.each(feature.getProperties().features, function item(idx, item) {

    //            var source = item.get('source').toLowerCase();

    //            var url = sources[source].url;
    //            var id = item.get('project_id').toLowerCase();
                
    //            popupContent += '<li style=""><a href="' + url + '/' + id + '" style="">' + item.get('project_name_' + document.documentElement.lang) + '</a></li>';
    //        });

    //        popupContent += '</ul></td></tr>';
    //        popupContent += '</table>';
    //        content.innerHTML = popupContent;


    //    } else if(cnt == 1) {

    //        title = Resources.project;

    //        popupContent = '<table class="map-popup map-table" style="width: 100%; white-space: normal;">';
    //        popupContent += '<tr style="vertical-align: top;"> <thead style="background: rgba(0,60,136,.5);color: #fff;"> <th style=""><strong>' + title + '</strong></th></thead>';

    //        popupContent += '<tr style="vertical-align: top;"><td style=""><ul style="padding-left: 20px; padding-right: 5px;">';

    //        var sources = [];

    //        $(config.layers).each(function (idx, layer) {
    //            sources[layer.source.toLowerCase()] = {
    //                id: layer.id,
    //                url: layer.url
    //            }
    //        });

    //        var props = feature;
    //        var source = props.get('source').toLowerCase();
    //        var url = sources[source].url;
    //        var id = props.get('project_id').toLowerCase();

    //        popupContent += '<li style=""><a href="' + url + '/' + id + '" style="">' + props.get('project_name_' + document.documentElement.lang) + '</a></li>';

    //        popupContent += '</ul></td></tr>';
    //        popupContent += '</table>';
    //        content.innerHTML = popupContent;

    //    }

    //    //Attempting to stop the popup from running out of the map area
    //    //var mapSize = $('#' + config.mapElement).data('map').getSize();
    //    //var popupDeadzoneX = 280;
    //    //var popupDeadzoneY = 74;
    //    //var placement = "right";
    //    //if (mapSize[1] - event.pixel[1] < popupDeadzoneY) {
    //    //    placement = "top";
    //    //    popup.setOffset([0, -25]);
    //    //}
    //    //else if (mapSize[0] - event.pixel[0] < popupDeadzoneX) {
    //    //    placement = "left";
    //    //    popup.setOffset([-10, -10]);
    //    //}
    //    //else {
    //    //    popup.setOffset([0, -10]);
    //    //}

    //    //popup.setPlacement(placement);
    //    popup.setPosition(event.coordinate);
    //},

    click: function (feature, config) {

        var cnt = 1;//feature.getProperties().features.length;

        if (cnt === 1) {

            var sources = [];

            $(config.layers).each(function (idx, layer) {
                sources[layer.source.toLowerCase()] = {
                    id: layer.id,
                    url: layer.url
                }
            });

            var props = feature;
            var source = props.get('source').toLowerCase();
            var url = sources[source].url;
            var project_id = props.get('project_id').toLowerCase();

            location.href = url + '/' + project_id;
        }
    },

    plot: function (longitude, latitude, icon) {

        var xformPoint = ol.proj.transform([longitude, latitude], 'EPSG:4326', 'EPSG:3857');

        var feature = new ol.Feature({
            geometry: new ol.geom.Point(xformPoint),
            name: 'Search'
        });

        var style = new ol.style.Style({
            image: new ol.style.Icon({
                scale: 0.50,
                src: icon
            })
        });

        var vectorSource = new ol.source.Vector({
            features: [feature]
        });

        return new ol.layer.Vector({
            source: vectorSource,
            style: style
        });
    },

    zoom: function (el, longitude, latitude) {

        var map = $(el).data('map');
        map.getView().setCenter(ol.proj.transform([longitude, latitude], 'EPSG:4326', 'EPSG:3857'));
        map.getView().setZoom(13.0);
    },

    addLayers: function (map, search, facets, layers) {

        var extent = ol.extent.createEmpty();

        $(layers).each(function (idx, layer) {
            if (!facets["source"] || (facets["source"] && (facets["source"] == layer.source))) {
                $(layer.el).show();
                olHelpers.addLayer(map, search, facets, layer, function (source) {
                    if (source.getFeatures().length > 0) {
                        ol.extent.extend(extent, source.getExtent());

                        var FitToResultsOptions = {
                            maxZoom: 6.0,
                            duration: 0,
                            padding: [5, 5, 5, 5],
                            size: map.getSize(),
                        };

                        //Zooms to fit the map pins.
                        if (initialMapLoad == false)
                            map.getView().fit(extent, FitToResultsOptions);
                        else
                        {
                            map.getView().fit([-14886644.184293684, 5206024.461292353, -5120696.576490585, 10892116.02759210]);
                            initialMapLoad = false;
                        }
                    }
                    $(layer.el).hide();
                });
            }
        });
    },

    addLayer: function (map, search, facets, layer, callback) {
        map.addLayer(olHelpers.createLayer(search, facets, layer, callback));
    },

    /**
     * Removes all layers current present on the given map.
     * 
     * @param {any} map The map to remove all layers from.
     */
    removeAllLayers: function (map) {

        try {

            var layers = map.getLayers();

            map.getLayers().forEach(function (layer, idx) {
                //Indices 0 and 1 are the basemap and basemap labels.
                if (idx > 1) layers.pop();
            });

        } catch (ex) {
            console.log(ex);
        }
    }



} : console.log('OpenLayers not available.');