
//Create alias for luxon as done in their documentation
var DateTime = luxon.DateTime;

$(document).ready(function () {

    if (typeof (ol) === 'undefined') {
        console.log('OpenLayers did not load correctly.');
        return;
    }

    var map = olHelpers.createMap(olConfig, []);
    var search = $('#searchString').val();

    olHelpers.addLayers(map, search, facets, olConfig.layers);
    $('#ol-geomap').data.map = map;
});

function ShowMap() {
    $("#show-map-button").removeClass("active");
    $('#show-map-button').html('<span class="fa fa-map-o" aria-hidden="true"></span> ' + Resources.HideMap);
    var wrapper = document.getElementById("map-wrapper");
    if (wrapper != null) {
        wrapper.style.display = "inline-block";
    }
}

function HideMap() {
    $("#show-map-button").addClass("active");
    $('#show-map-button').html('<span class="fa fa-map-o" aria-hidden="true"></span> ' + Resources.ShowMap);
    var wrapper = document.getElementById("map-wrapper");
    if (wrapper != null) {
        wrapper.style.display = "none";
    }
}

function UpdateMap(search, facets) {
    var map = $('#ol-geomap').data.map;

    olHelpers.removeAllLayers(map);
    olHelpers.addLayers(map, search, facets, olConfig.layers);
}

function UpdatePager(docCount) {
    // Update the pagination
    var totalPages = Math.ceil(docCount / pageSize);

    if (!currentPage) {
        currentPage = 1;
    }

    if (totalPages <= 1) {
        $("#paginationFooter").html('');
        return;
    }

    // Set a max of 5 items and set the current page in middle of pages
    var startPage = currentPage;
    if ((startPage == 1) || (startPage == 2))
        startPage = 1;
    else
        startPage -= 2;

    var maxPage = startPage + 5;
    if (totalPages < maxPage)
        maxPage = totalPages + 1;
    var backPage = parseInt(currentPage) - 1;
    if (backPage < 1)
        backPage = 1;
    var forwardPage = parseInt(currentPage) + 1;
    var htmlString;
    if (currentPage == 1) {
        htmlString = '';
    }
    else if (currentPage > 3) {
        htmlString = '<li><a href="javascript:void(0)" onclick="GoToPage(\'' + backPage + '\')" rel="prev">' + Resources.Previous + '</a></li>';
        htmlString += '<li><a href="javascript:void(0)" onclick="GoToPage(\'' + 1 + '\')" rel="prev">1</a></li>';
    }
    else {
        htmlString = '<li><a href="javascript:void(0)" onclick="GoToPage(\'' + backPage + '\')" rel="prev">' + Resources.Previous + '</a></li>';
    }

    for (var i = startPage; i < maxPage; i++) {
        if (i == currentPage)
            htmlString += '<li  class="active"><a href="#">' + i + '</a></li>';
        else
            htmlString += '<li><a href="javascript:void(0)" onclick="GoToPage(\'' + parseInt(i) + '\')">' + i + '</a></li>';
    }

    if (currentPage == totalPages) {
        htmlString += '';
    }
    else if (totalPages - currentPage >= 5) {

        htmlString += '<li><a href="javascript:void(0)" onclick="GoToPage(\'' + totalPages + '\')" >' + totalPages + '</a ></li > ';
        htmlString += '<li><a href="javascript:void(0)" onclick="GoToPage(\'' + forwardPage + '\')" rel="next">' + Resources.Next + '</a></li>';
    }
    else {
        htmlString += '<li><a href="javascript:void(0)" onclick="GoToPage(\'' + forwardPage + '\')" rel="next">' + Resources.Next + '</a></li>';
    }


    $("#paginationFooter").html(htmlString);
}

function GoToPage(page) {
    currentPage = page;
    Search();
}

function UpdateFacet(facetName, data) {
    var facetResultsHTML = '';

    for (var i = 0; i < data.length; i++) {
        if (facets[facetName] != null) {
            var values = decodeData(facets[facetName]).split("@");
            if (values.indexOf(data[i].Value) > -1 || (facets[facetName] == Resources.NoFacetValue && data[i].Value == "")) {
                facetResultsHTML += '<li class="list-group-item"><a href="javascript:void(0)" class="activeFacet" onclick=\'RemoveFacet(\"' + facetName + '\",\"' + (encodeData(data[i].Value.toString()) || Resources.NoFacetValue) + '\");\'><span class="checkbox checkbox-checked"></span><span class="badge">' + data[i].Count + '</span><span class="wb-inv"> results </span></span>' + SharedResource(decodeURIComponent(data[i].Value.toString().replace(/\+/g, '%20') || Resources.NoFacetValueLabel)) + '</a></li>';
            }
            else
                facetResultsHTML += '<li class="list-group-item"><a href="javascript:void(0)" class="inactiveFacet" onclick=\'ChooseFacet(\"' + facetName + '\",\"' + (encodeData(data[i].Value.toString()) || Resources.NoFacetValue) + '\");\'><span class="checkbox checkbox-unchecked"></span><span class="badge">' + data[i].Count + '</span><span class="wb-inv"> results </span>' + SharedResource(decodeURIComponent(data[i].Value.toString().replace(/\+/g, '%20') || Resources.NoFacetValueLabel)) + '</a></li>';
        }
        else {
            facetResultsHTML += '<li class="list-group-item"><a href="javascript:void(0)" class="inactiveFacet" onclick=\'ChooseFacet(\"' + facetName + '\",\"' + (encodeData(data[i].Value.toString()) || Resources.NoFacetValue) + '\");\'><span class="checkbox checkbox-unchecked"></span><span class="badge">' + data[i].Count + '</span><span class="wb-inv"> results </span></span>' + SharedResource(decodeURIComponent(data[i].Value.toString().replace(/\+/g, '%20') || Resources.NoFacetValueLabel)) + '</a></li>';
        }
    }

        $("#" + facetName + "_facets").html(facetResultsHTML);

    if (data.length > 0) {
        $("#" + facetName + "_hider").removeAttr("hidden");
    }
    else {
        $("#" + facetName + "_hider").attr('hidden', '');
    }
}

function ChooseFacet(facetName, data) {
    if (facets[facetName] != null)
        facets[facetName] += "@" + data;
    else
        facets[facetName] = data;

    currentPage = 1;
    Search();

    if (isMobileDevice())
        //document.getElementById(facetName + 'FacetTitle').scrollIntoView();
        document.getElementById('results-filter-wrapper').scrollIntoView();
}

function isMobileDevice() {
    if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent))
        return true;
    else
        return false;
}

function RemoveFacet(facet) {
    facets[facet] = null;
    currentPage = 1;
    Search();
}

function RemoveFacet(facet, value) {
    // Remove a facet
    if (facets[facet] != null && facets[facet].toString().indexOf("@") > -1) {
        facets[facet] = facets[facet].split("@").filter(
            function (e) {
                return (e !== value && !isNullOrWhitespace(e));
            }).join("@");
    }
    else
        facets[facet] = null;

    currentPage = 1;
    Search();
}

function RemoveAllFacets() {
    var anchors = document.querySelectorAll('a.activeFacet');
    for (var i = 0; i < anchors.length; i++) {
        {
            try {
                key = anchors[i].attributes.onclick.value.toString().match(/"([^"]+)"/)[1];
                facets[key] = null;
            }
            catch (e) {
                continue;
            }
        }
    }
    currentPage = 1;
    Search();
}

var DateFilterFlag = false;
function ApplyDateFilter(startDate, endDate, search = true) {

    document.getElementById("dateFilterButton").disabled = true;
    console.log(startDate.value);
    console.log(endDate.value);

    if (DateFilterFlag || isNullOrWhitespace(startDate.value) || isNullOrWhitespace(endDate.value)) {
        document.getElementById("dateFilterButton").innerText = Resources.ApplyFilter;
        document.getElementById("startDateFilter").disabled = false;
        document.getElementById("endDateFilter").disabled = false;

        startDate.value = "";
        endDate.value = "";
        dateRange = void 0;
        DateFilterFlag = false;
    }
    else {
        document.getElementById("dateFilterButton").innerText = Resources.ClearFilter;
        document.getElementById("startDateFilter").disabled = true;
        document.getElementById("endDateFilter").disabled = true;

        //Swap Date values if startDate is later.
        if (startDate.value > endDate.value) {
            var temp = startDate.value;
            startDate.value = endDate.value;
            endDate.value = temp;
        }

        dateRange = [startDate.value, endDate.value];
        DateFilterFlag = true;
    }
  
    if (search) {
        currentPage = 1;
        Search();
    }
    document.getElementById("dateFilterButton").disabled = false;
    console.log(DateFilterFlag);
}

function DecodeHtml(str) {
    return $('<div/>').html(str).text();
}

function ChangeListAllDocumentsFilter(value, search = true) {
    if (typeof (projectID) === 'undefined') {
        projectID = value;
        $("#AllDocumentsCheckBox").removeClass("checkbox-unchecked").addClass("checkbox-checked");
        $("#projectDocumentsInput").prop('disabled', false);
        $("#documentTypeInput").prop('disabled', false);
        $("#mainHeader").html(projectName);
    }
    else {
        projectID = void (0);
        $("#AllDocumentsCheckBox").removeClass("checkbox-checked").addClass("checkbox-unchecked");
        $("#projectDocumentsInput").prop('disabled', true);
        $("#documentTypeInput").prop('disabled', true);
        $("#mainHeader").html(Resources.SearchRegistry);
    }
    if (search) {
        currentPage = 1;
        Search()
    }
}

function ChangeActiveProjectsFilter(search = true) {
    if (activeProjects === false) {
        activeProjects = true;
        $("#ActiveProjectsCheckBox").removeClass("checkbox-unchecked").addClass("checkbox-checked");
        $("#activeProjectsInput").prop('disabled', false);
    }
    else {
        activeProjects = false;
        $("#ActiveProjectsCheckBox").removeClass("checkbox-checked").addClass("checkbox-unchecked");
        $("#activeProjectsInput").prop('disabled', true);
    }
    if (search) {
        currentPage = 1;
        Search()
    }
}

function ChangeInactiveProjectsFilter(search = true) {
    if (inactiveProjects === false || inactiveProjects === undefined) {
        inactiveProjects = true;
        $("#InactiveProjectsCheckBox").removeClass("checkbox-unchecked").addClass("checkbox-checked");
        $("#inactiveProjectsInput").prop('disabled', false);
    }
    else {
        inactiveProjects = false;
        $("#InactiveProjectsCheckBox").removeClass("checkbox-checked").addClass("checkbox-unchecked");
        $("#inactiveProjectsInput").prop('disabled', true);
    }
    if (search)
    {
        currentPage = 1;
        Search()
    }
}

function ChangeFedLandsFilter(search = true) {
    if (fedLands === false) {
        fedLands = true;
        $("#FedLandsCheckBox").removeClass("checkbox-unchecked").addClass("checkbox-checked");
        $("#activeProjectsInput").prop('disabled', false);
    }
    else {
        fedLands = false;
        $("#FedLandsCheckBox").removeClass("checkbox-checked").addClass("checkbox-unchecked");
        $("#fedLandsInput").prop('disabled', true);
    }
    if (search) {
        currentPage = 1;
        Search()
    }
}

function ChangePermitsFilter(search = true) {
    if (permits === false) {
        permits = true;
        $("#PermitsCheckBox").removeClass("checkbox-unchecked").addClass("checkbox-checked");
        $("#activeProjectsInput").prop('disabled', false);
    }
    else {
        permits = false;
        $("#PermitsCheckBox").removeClass("checkbox-checked").addClass("checkbox-unchecked");
        $("#PermitsInput").prop('disabled', true);
    }
    if (search) {
        currentPage = 1;
        Search()
    }
}

function ChangeRAFilter() {

    if (regionalAssessments === false || regionalAssessments === undefined) {
        regionalAssessments = true;
        $("#regionalAssessmentCheckBox").removeClass("checkbox-unchecked").addClass("checkbox-checked");
        $("#regionalAssessmentInput").prop('disabled', false);
        if (isFrench === true) {
            ChooseFacet("ea_type_fr", "Regional Assessment");
            ChooseFacet("ea_type_fr", "Évaluation stratégique");
            ChooseFacet("ea_type_fr", "Demande d'évaluation régionale");
        }
        else { 
            ChooseFacet("ea_type_en", "Regional Assessment");
            ChooseFacet("ea_type_en", "Strategic assessment");
            ChooseFacet("ea_type_en", "Request for regional assessment");
        }
    }
    else {
        regionalAssessments = false;
        $("#regionalAssessmentCheckBox").removeClass("checkbox-checked").addClass("checkbox-unchecked");
        $("#regionalAssessmentInput").prop('disabled', true);
        if (isFrench === true) {
            RemoveFacet("ea_type_fr", "Évaluation régionale");
            RemoveFacet("ea_type_fr", "Évaluation stratégique");
            RemoveFacet("ea_type_fr", "Demande d'évaluation régionale");
        }
        else {
            RemoveFacet("ea_type_en", "Regional Assessment");
            RemoveFacet("ea_type_en", "Strategic assessment");
            RemoveFacet("ea_type_en", "Request for regional assessment");
        }
    }
    currentPage = 1;
    Search()
}


function SortBy(sortName) {
    sortType = sortName;
    currentPage = 1;
    Search();
}


$('.results-sortby-group a.btn').click(function () {

    var sortType = (this.id);
    var sortOrder;
    var isActive = this.classList.contains("active")

    if (this.classList.contains("asc")) {
        (isActive ? sortOrder = "Desc" : sortOrder = "Asc");

        if (isActive) {
            $(this).removeClass("asc").addClass("desc");
            $(this.firstElementChild).removeClass("fa-sort-asc").addClass("fa-sort-desc");
        }
    }

    else if (this.classList.contains("desc")) {
        (isActive ? sortOrder = "Asc" : sortOrder = "Desc");

        if (isActive) {
            $(this).removeClass("desc").addClass("asc");
            $(this.firstElementChild).removeClass("fa-sort-desc").addClass("fa-sort-asc");
        }
    }

    else {
        sortOrder = "";
    }

    sortType += sortOrder;

    $('.results-sortby-group a.btn').each(function () {
        $(this).removeClass('active');
    });
    $(this).addClass('active');
    SortBy(sortType);
});

function isNullOrWhitespace(input) {
    return !input || !input.trim();
}

function stripHTML(html) {
    var tmp = document.createElement("DIV");
    tmp.innerHTML = html.toString().replace("&lt;", "<").replace("&gt;", ">");
    return tmp.textContent || tmp.innerText || "";
}

function removeUnicode(text) {
    var re = /[\0-\x1F\x7F-\x9F\xAD\u0378\u0379\u037F-\u0383\u038B\u038D\u03A2\u0528-\u0530\u0557\u0558\u0560\u0588\u058B-\u058E\u0590\u05C8-\u05CF\u05EB-\u05EF\u05F5-\u0605\u061C\u061D\u06DD\u070E\u070F\u074B\u074C\u07B2-\u07BF\u07FB-\u07FF\u082E\u082F\u083F\u085C\u085D\u085F-\u089F\u08A1\u08AD-\u08E3\u08FF\u0978\u0980\u0984\u098D\u098E\u0991\u0992\u09A9\u09B1\u09B3-\u09B5\u09BA\u09BB\u09C5\u09C6\u09C9\u09CA\u09CF-\u09D6\u09D8-\u09DB\u09DE\u09E4\u09E5\u09FC-\u0A00\u0A04\u0A0B-\u0A0E\u0A11\u0A12\u0A29\u0A31\u0A34\u0A37\u0A3A\u0A3B\u0A3D\u0A43-\u0A46\u0A49\u0A4A\u0A4E-\u0A50\u0A52-\u0A58\u0A5D\u0A5F-\u0A65\u0A76-\u0A80\u0A84\u0A8E\u0A92\u0AA9\u0AB1\u0AB4\u0ABA\u0ABB\u0AC6\u0ACA\u0ACE\u0ACF\u0AD1-\u0ADF\u0AE4\u0AE5\u0AF2-\u0B00\u0B04\u0B0D\u0B0E\u0B11\u0B12\u0B29\u0B31\u0B34\u0B3A\u0B3B\u0B45\u0B46\u0B49\u0B4A\u0B4E-\u0B55\u0B58-\u0B5B\u0B5E\u0B64\u0B65\u0B78-\u0B81\u0B84\u0B8B-\u0B8D\u0B91\u0B96-\u0B98\u0B9B\u0B9D\u0BA0-\u0BA2\u0BA5-\u0BA7\u0BAB-\u0BAD\u0BBA-\u0BBD\u0BC3-\u0BC5\u0BC9\u0BCE\u0BCF\u0BD1-\u0BD6\u0BD8-\u0BE5\u0BFB-\u0C00\u0C04\u0C0D\u0C11\u0C29\u0C34\u0C3A-\u0C3C\u0C45\u0C49\u0C4E-\u0C54\u0C57\u0C5A-\u0C5F\u0C64\u0C65\u0C70-\u0C77\u0C80\u0C81\u0C84\u0C8D\u0C91\u0CA9\u0CB4\u0CBA\u0CBB\u0CC5\u0CC9\u0CCE-\u0CD4\u0CD7-\u0CDD\u0CDF\u0CE4\u0CE5\u0CF0\u0CF3-\u0D01\u0D04\u0D0D\u0D11\u0D3B\u0D3C\u0D45\u0D49\u0D4F-\u0D56\u0D58-\u0D5F\u0D64\u0D65\u0D76-\u0D78\u0D80\u0D81\u0D84\u0D97-\u0D99\u0DB2\u0DBC\u0DBE\u0DBF\u0DC7-\u0DC9\u0DCB-\u0DCE\u0DD5\u0DD7\u0DE0-\u0DF1\u0DF5-\u0E00\u0E3B-\u0E3E\u0E5C-\u0E80\u0E83\u0E85\u0E86\u0E89\u0E8B\u0E8C\u0E8E-\u0E93\u0E98\u0EA0\u0EA4\u0EA6\u0EA8\u0EA9\u0EAC\u0EBA\u0EBE\u0EBF\u0EC5\u0EC7\u0ECE\u0ECF\u0EDA\u0EDB\u0EE0-\u0EFF\u0F48\u0F6D-\u0F70\u0F98\u0FBD\u0FCD\u0FDB-\u0FFF\u10C6\u10C8-\u10CC\u10CE\u10CF\u1249\u124E\u124F\u1257\u1259\u125E\u125F\u1289\u128E\u128F\u12B1\u12B6\u12B7\u12BF\u12C1\u12C6\u12C7\u12D7\u1311\u1316\u1317\u135B\u135C\u137D-\u137F\u139A-\u139F\u13F5-\u13FF\u169D-\u169F\u16F1-\u16FF\u170D\u1715-\u171F\u1737-\u173F\u1754-\u175F\u176D\u1771\u1774-\u177F\u17DE\u17DF\u17EA-\u17EF\u17FA-\u17FF\u180F\u181A-\u181F\u1878-\u187F\u18AB-\u18AF\u18F6-\u18FF\u191D-\u191F\u192C-\u192F\u193C-\u193F\u1941-\u1943\u196E\u196F\u1975-\u197F\u19AC-\u19AF\u19CA-\u19CF\u19DB-\u19DD\u1A1C\u1A1D\u1A5F\u1A7D\u1A7E\u1A8A-\u1A8F\u1A9A-\u1A9F\u1AAE-\u1AFF\u1B4C-\u1B4F\u1B7D-\u1B7F\u1BF4-\u1BFB\u1C38-\u1C3A\u1C4A-\u1C4C\u1C80-\u1CBF\u1CC8-\u1CCF\u1CF7-\u1CFF\u1DE7-\u1DFB\u1F16\u1F17\u1F1E\u1F1F\u1F46\u1F47\u1F4E\u1F4F\u1F58\u1F5A\u1F5C\u1F5E\u1F7E\u1F7F\u1FB5\u1FC5\u1FD4\u1FD5\u1FDC\u1FF0\u1FF1\u1FF5\u1FFF\u200B-\u200F\u202A-\u202E\u2060-\u206F\u2072\u2073\u208F\u209D-\u209F\u20BB-\u20CF\u20F1-\u20FF\u218A-\u218F\u23F4-\u23FF\u2427-\u243F\u244B-\u245F\u2700\u2B4D-\u2B4F\u2B5A-\u2BFF\u2C2F\u2C5F\u2CF4-\u2CF8\u2D26\u2D28-\u2D2C\u2D2E\u2D2F\u2D68-\u2D6E\u2D71-\u2D7E\u2D97-\u2D9F\u2DA7\u2DAF\u2DB7\u2DBF\u2DC7\u2DCF\u2DD7\u2DDF\u2E3C-\u2E7F\u2E9A\u2EF4-\u2EFF\u2FD6-\u2FEF\u2FFC-\u2FFF\u3040\u3097\u3098\u3100-\u3104\u312E-\u3130\u318F\u31BB-\u31BF\u31E4-\u31EF\u321F\u32FF\u4DB6-\u4DBF\u9FCD-\u9FFF\uA48D-\uA48F\uA4C7-\uA4CF\uA62C-\uA63F\uA698-\uA69E\uA6F8-\uA6FF\uA78F\uA794-\uA79F\uA7AB-\uA7F7\uA82C-\uA82F\uA83A-\uA83F\uA878-\uA87F\uA8C5-\uA8CD\uA8DA-\uA8DF\uA8FC-\uA8FF\uA954-\uA95E\uA97D-\uA97F\uA9CE\uA9DA-\uA9DD\uA9E0-\uA9FF\uAA37-\uAA3F\uAA4E\uAA4F\uAA5A\uAA5B\uAA7C-\uAA7F\uAAC3-\uAADA\uAAF7-\uAB00\uAB07\uAB08\uAB0F\uAB10\uAB17-\uAB1F\uAB27\uAB2F-\uABBF\uABEE\uABEF\uABFA-\uABFF\uD7A4-\uD7AF\uD7C7-\uD7CA\uD7FC-\uF8FF\uFA6E\uFA6F\uFADA-\uFAFF\uFB07-\uFB12\uFB18-\uFB1C\uFB37\uFB3D\uFB3F\uFB42\uFB45\uFBC2-\uFBD2\uFD40-\uFD4F\uFD90\uFD91\uFDC8-\uFDEF\uFDFE\uFDFF\uFE1A-\uFE1F\uFE27-\uFE2F\uFE53\uFE67\uFE6C-\uFE6F\uFE75\uFEFD-\uFF00\uFFBF-\uFFC1\uFFC8\uFFC9\uFFD0\uFFD1\uFFD8\uFFD9\uFFDD-\uFFDF\uFFE7\uFFEF-\uFFFB\uFFFE\uFFFF]/g;
    return text.replace(re, " ");
}

function encodeData(s) {
    return encodeURIComponent(s).replace(/\-/g, "%2D").replace(/\_/g, "%5F").replace(/\./g, "%2E").replace(/\!/g, "%21").replace(/\~/g, "%7E").replace(/\*/g, "%2A").replace(/\'/g, "%27").replace(/\(/g, "%28").replace(/\)/g, "%29");
}

function decodeData(s) {
    try {
        return decodeURIComponent(s.replace(/\%2D/g, "-").replace(/\%5F/g, "_").replace(/\%2E/g, ".").replace(/\%21/g, "!").replace(/\%7E/g, "~").replace(/\%2A/g, "*").replace(/\%27/g, "'").replace(/\%28/g, "(").replace(/\%29/g, ")"));
    } catch (e) {
    }
    return "";
}

function UpdateProjectDetails(data) {
    var projectDetailsHTML = '';
    var readMoreStr = " ...";
    var spacerStr = (document.documentElement.lang == 'en') ? ": " : " : "
    var documentResultContentLength = 500;
    var projectResultContentLength = 500;
    var archiveResultContentLength = 1000;
    var commentResultContentLength = 250;
    var attachmentResultContentLength = 250;

    var count = 0;
    //if (data.Facets["document_type"] != null) {
    //    for (var i = 0; (i < data.Facets["document_type"].length); i++) {
    //        count += data.Facets["document_type"][i].Count;
    //    }
    //}
    //else {
    //    count = data["Count"];
    //}
    count = data["Count"];

    $("#projects-found").html(count);

    var resultCountText = Resources.ResultsLbl;
    if (count == 1)
        resultCountText = Resources.ResultLbl;
    $("#result-count-lbl").text(decodeURIComponent(resultCountText));

    for (var i = 0; (i < data.Results.length && i < pageSize); i++) {
        if (data.Results[i].Document.document_type == "project") {
            projectDetailsHTML += '<article><a class="resultJobItem" href="' + registrySite + 'proj/' + data.Results[i].Document.project_id + '">';

            projectDetailsHTML += '<h3 class="title"><span class="job-source glyphicon glyphicon-globe"><span class="wb-inv">Project</span></span><span class="noctitle">' + data.Results[i].Document.project_name + '</span></h3>';
            projectDetailsHTML += '<ul class="list-unstyled">';
            projectDetailsHTML += '<li class="location"><span class="wb-inv">Location</span>';

            var locationLabel = "";
            for (var x = 0; x < data.Results[i].Document.location.length; x++) {
                if (!isNullOrWhitespace(data.Results[i].Document.location[x])) {
                    if (data.Results[i].Document.location[x] == "Location not applicable" || data.Results[i].Document.location[x] == "Emplacement non applicable" || data.Results[i].Document.location[x] == "Canada-wide" || data.Results[i].Document.location[x] == "Pancanadien") {
                        locationLabel += " (" + data.Results[i].Document.location[x] + ")";
                    }
                    else if (x < data.Results[i].Document.province.length) {
                        locationLabel += " (" + data.Results[i].Document.location[x] + ", " + data.Results[i].Document.province[x] + ")";
                    }
                    else {
                        locationLabel += " (" + data.Results[i].Document.location[x] + ")";
                    }
                }
                else if (x < data.Results[i].Document.province.length && !isNullOrWhitespace(data.Results[i].Document.province[x])) {
                    locationLabel += " (" + data.Results[i].Document.province[x] + ")";
                }
            }
            projectDetailsHTML += locationLabel + '<br>' + '</li>';

            var eaType = !(isNullOrWhitespace(data.Results[i].Document.ea_type)) ? data.Results[i].Document.ea_type : Resources.NoEaType;
            projectDetailsHTML += '<li class="salary"><strong>' + Resources.EaType + spacerStr + '</strong> ' + eaType;
            projectDetailsHTML += '<li class="salary"><strong>' + Resources.Status + spacerStr + '</strong> ' + data.Results[i].Document.status + '</li>';
            projectDetailsHTML += '<li class="salary"><strong>' + Resources.DocRefNum + spacerStr + '</strong> ' + (data.Results[i].Document.project_id) + '</li>';

            var date = new Date(parseInt(data.Results[i].Document.updated_at.substr(6)));
            projectDetailsHTML += '<li class="salary"><strong>' + Resources.Modified + spacerStr + '</strong> ' + date.toJSON().split('T')[0] + '</li>';
            projectDetailsHTML += '<li class="salary relevance_score"><strong>' + Resources.Relevance + spacerStr + '</strong> ' + (data.Results[i]["Score"].toFixed(4) * 100.0) + '</li>';

            var projectDesc = data.Results[i].Document.description || "";

            if (projectDesc.indexOf(" ") == -1)
                projectDesc += " ";

            if (projectDesc.length > projectResultContentLength)
                projectDesc = projectDesc.substring(0, projectDesc.substring(0, projectResultContentLength).lastIndexOf(' ') + 1) + readMoreStr;
            projectDesc = stripHTML(projectDesc);

            if (data.Results[i]["Highlights"] != null && data.Results[i]["Highlights"]["description_" + document.documentElement.lang] != null)
                projectDesc = (stripHTML(data.Results[i]["Highlights"]["description_" + document.documentElement.lang]).toString().replace(/___HighlightPreTag___/g, '<span class=\"bg-info\">').replace(/___HighlightPostTag___/g, '</span>'));

            projectDetailsHTML += '<li class="business">' + projectDesc + '</li>';
            projectDetailsHTML += '</ul>';
            projectDetailsHTML += '</a></article>';
        }

        else if (data.Results[i].Document.document_type == "document") {

            projectDetailsHTML += '<article><div class="resultJobItem">';
            projectDetailsHTML += '<a class="wrapper document-wrapper" href="' + registrySite + 'document/' + data.Results[i].Document.document_id + '">';

            projectDetailsHTML += '<h3 class="title"><span class="job-source glyphicon glyphicon-file"><span class="wb-inv">Document</span></span><span class="noctitle">' + decodeURIComponent(data.Results[i].Document.document_title.replace(/\+/g, '%20')) + '</span></h3>';
            projectDetailsHTML += '<ul class="list-unstyled">';
            projectDetailsHTML += '<li class="location"><span class="wb-inv">Project</span>' + decodeURIComponent(data.Results[i].Document.project_name.replace(/\+/g, '%20')) + '</li >';

            projectDetailsHTML += '<li class="salary"><strong>' + Resources.DocumentCategory + spacerStr + '</strong> ' + decodeURIComponent(data.Results[i].Document.document_category.replace(/\+/g, '%20')) + '</li>';

            var fileName = data.Results[i].Document.metadata_storage_path;
            var extension = fileName.substring(fileName.lastIndexOf('.') + 1).toUpperCase();

            // Parse the input string
            var dt = DateTime.fromFormat(data.Results[i].Document.metadata_storage_last_modified, "M/d/yyyy h:mm:ss a Z");
            // Format as YYYY-dd-mm
            var blobDate = dt.toFormat("yyyy-MM-dd");

            //projectDetailsHTML += '<li class="salary"><strong>' + "Document ID" + spacerStr + '</strong> ' + (data.Results[i].Document.document_id) + '</li>';
            projectDetailsHTML += '<li class="salary"><strong>' + Resources.DocRefNum + spacerStr + '</strong> ' + (data.Results[i].Document.doc_ref) + '</li>';

            var date = new Date(parseInt(data.Results[i].Document.updated_at.substr(6)));

            projectDetailsHTML += '<li class="salary"><strong>' + Resources.DocumentDate + spacerStr + '</strong> ' + date.toJSON().split('T')[0] + '</li>';
            //projectDetailsHTML += '<li class="salary"><strong>' + Resources.Modified + spacerStr + '</strong> ' + blobDate + '</li>';

            //projectDetailsHTML += '<li class="salary"><strong>' + Resources.FileType + spacerStr + '</strong> ' + extension + '</li>';
            projectDetailsHTML += '<li class="salary"><strong>' + "Document" + spacerStr + '</strong> ' + (data.Results[i].Document.metadata_storage_path.split("/").pop()) + '</li>';

            projectDetailsHTML += '<li class="salary relevance_score"><strong>' + Resources.Relevance + spacerStr + '</strong> ' + (data.Results[i]["Score"].toFixed(4) * 100.0) + '</li>';


            var projectDesc = data.Results[i].Document.content || "";
            if (projectDesc.indexOf(" ") == -1)
                projectDesc += " ";

            if (projectDesc.length > documentResultContentLength)
                projectDesc = projectDesc.substring(0, projectDesc.substring(0, documentResultContentLength).lastIndexOf(' ') + 1) + readMoreStr;

            projectDesc = '<li class="business">' + stripHTML(projectDesc); + '</li>';

            if (data.Results[i]["Highlights"] != null && data.Results[i]["Highlights"]["content"] != null) {
                projectDesc = "";
                for (var y = 0; y < data.Results[i]["Highlights"].content.length; y++) {
                    var highlightItem = removeUnicode(stripHTML(data.Results[i]["Highlights"].content[y].toString()).replace(/___HighlightPreTag___/g, '<span class=\"bg-info\">').replace(/___HighlightPostTag___/g, '</span>'));
                    projectDesc += '<li class="business merged_result">' + highlightItem + '</li>';
                }
            }
            projectDetailsHTML += projectDesc;
            projectDetailsHTML += '</ul></a>';

            if (data.Results[i].Document.duplicates_removed != null && data.Results[i].Document.duplicates_removed.length > 0) {
                var attachmentCnt = data.Results[i].Document.duplicates_removed.length;
                var relatedResultsMsg = (attachmentCnt == 1) ? Resources.AlternateFormatLbl : Resources.AlternateFormatPluralLbl;

                projectDetailsHTML += '<div id="collapse_' + data.Results[i].Document.document_id + '">';
                projectDetailsHTML += '<details class="duplicate_collapser"><summary class="salary duplicate_collapser_title">' + attachmentCnt + " " + relatedResultsMsg + '</summary>';
                projectDetailsHTML += '<div class="wb-tabs"><div class="tabpanels">'

                for (var x = 0; x < attachmentCnt; x++) {

                    var attachment = data.Results[i].Document.duplicates_removed[x];
                    var filename = attachment.metadata_storage_path.split("/").pop();
                    var extension = filename.substring(filename.lastIndexOf('.') + 1).toUpperCase();

                    projectDetailsHTML += '<details id="details-panel_' + attachment.document_id + x + '">';

                    var language = Resources.english;
                    if (attachment.language != "english")
                        language = Resources.french;

                    if (document.documentElement.lang == 'en')
                        projectDetailsHTML += '<summary>' + language + ' ' + extension + '</summary>';
                    else
                        projectDetailsHTML += '<summary>' + extension + ' ' + language + '</summary>';
                    projectDetailsHTML += '<ul class="list-unstyled">'

                    //projectDetailsHTML += '<li class="salary document_name duplicate"><strong>Document'+ spacerStr + '</strong>' + filename + '</li>';
                    //projectDetailsHTML += '<li class="salary relevance_score duplicate"><strong>' + Resources.Relevance + spacerStr + '</strong> ' + (attachment.Score * 100) + '</li>';

                    var attachmentDesc = attachment.content || "";
                    if (attachmentDesc.indexOf(" ") == -1)
                        attachmentDesc += " ";

                    if (attachmentDesc.length > documentResultContentLength)
                        attachmentDesc = attachmentDesc.substring(0, attachmentDesc.substring(0, documentResultContentLength).lastIndexOf(' ') + 1) + readMoreStr;
                    attachmentDesc = '<li class="business merged_result duplicate">' + stripHTML(attachmentDesc) + '</li>';

                    if (attachment["Highlights"] != null && attachment["Highlights"]["content"] != null) {
                        attachmentDesc = "";
                        for (var y = 0; y < attachment["Highlights"]["content"].length; y++) {
                            var highlightItem = removeUnicode(stripHTML(attachment["Highlights"].content[y].toString()).replace(/___HighlightPreTag___/g, '<span class=\"bg-info\">').replace(/___HighlightPostTag___/g, '</span>'));
                            attachmentDesc += '<li class="business merged_result duplicate">' + highlightItem + '</li>';
                        }
                    }
                    projectDetailsHTML += attachmentDesc;
                    projectDetailsHTML += '</ul></details >';

                }
                projectDetailsHTML += '</div></div></div></details>';

            }

            //if (data.Results[i].Document.metadata_content_type != null && data.Results[i].Document.metadata_content_type.indexOf("text/html") >= 0)
            //{
            //    var downloadUrl = data.Results[i].Document.metadata_storage_path;
            //    projectDetailsHTML += '<a href="' + downloadUrl + '">' + '<ul class="list-unstyled"> <li>' + Resources.DownloadDocument + '</li></ul></a >';
            //}

            projectDetailsHTML += '</div></article>';
        }
        else if (data.Results[i].Document.document_type == "comment" || data.Results[i].Document.document_type == "attachment") {
            var icon = (data.Results[i].Document.document_type == "comment") ? "glyphicon-comment" : "glyphicon-paperclip";
            projectDetailsHTML += '<article><div class="resultJobItem">';
            projectDetailsHTML += '<a class="wrapper document-wrapper" href="' + registrySite + 'proj/' + data.Results[i].Document.project_id + "/contributions/id/" + data.Results[i].Document.comment_id + '">';

            projectDetailsHTML += '<h3 class="title"><span class="job-source glyphicon ' + icon + '"><span class="wb-inv">Comment</span></span><span class="noctitle">' + decodeURIComponent(data.Results[i].Document.comment_title.replace(/\+/g, '%20').replace(/\%/g, '%25')) + '</span></h3>';
            projectDetailsHTML += '<ul class="list-unstyled">';
            projectDetailsHTML += '<li class="location"><span class="wb-inv">Comment</span><strong>' + decodeURIComponent((data.Results[i].Document.project_name || "").replace(/\+/g, '%20')) + '</strong></li >';

            projectDetailsHTML += '<li class="salary"><strong>' + Resources.lblCommentAuthor + spacerStr + '</strong> ' + decodeURIComponent((data.Results[i].Document.submitted_by || "").replace(/\+/g, '%20')) + '</li>';

            var fileName = data.Results[i].Document.metadata_storage_path || "";
            var extension = fileName.substring(fileName.lastIndexOf('.') + 1).toUpperCase();

            //projectDetailsHTML += '<li class="salary"><strong>' + "Comment ID" + spacerStr + '</strong> ' + (data.Results[i].Document.project_id) + "-" + (data.Results[i].Document.comment_id) + '</li>';
            projectDetailsHTML += '<li class="salary"><strong>' + Resources.DocRefNum + spacerStr + '</strong> ' + (data.Results[i].Document.doc_ref) + '</li>';

            //var date = new Date(parseInt(data.Results[i].Document.updated_at.substr(6)));

            var date = new Date(parseInt(data.Results[i].Document.comment_submitted_date.substr(6)));

            if (document.documentElement.lang == 'fr')
                if (date.getMilliseconds() == 0 && date.getMinutes() == 0 && date.getSeconds() == 0)
                    projectDetailsHTML += '<li class="salary"><strong>' + Resources.lblCommentSubmitted + spacerStr + '</strong> ' + DateTime.fromJSDate(date).toUTC().toFormat('yyyy-MM-dd') + '</li>';
                else
                    projectDetailsHTML += '<li class="salary"><strong>' + Resources.lblCommentSubmitted + spacerStr + '</strong> ' + DateTime.fromJSDate(date).toUTC().toFormat("yyyy-MM-dd H 'h' mm") + '</li>';
            else
                if (date.getMilliseconds() == 0 && date.getMinutes() == 0 && date.getSeconds() == 0)
                    projectDetailsHTML += '<li class="salary"><strong>' + Resources.lblCommentSubmitted + spacerStr + '</strong> ' + DateTime.fromJSDate(date).toUTC().toFormat('yyyy-MM-dd') + '</li>';
                else
                    projectDetailsHTML += '<li class="salary"><strong>' + Resources.lblCommentSubmitted + spacerStr + '</strong> ' + DateTime.fromJSDate(date).toUTC().toFormat('yyyy-MM-dd - h:mm a') + '</li>';

            if (data.Results[i].Document.rationale_id != null) {


                var date2 = new Date(parseInt(data.Results[i].Document.comment_edit_date.substr(6)));

                if (document.documentElement.lang == 'fr')
                    projectDetailsHTML += '<li class="salary"><strong>' + Resources.Updated + spacerStr + '</strong> ' + DateTime.fromJSDate(date2).toUTC().toFormat("yyyy-MM-dd H 'h' mm") + '</li>';
                else
                    projectDetailsHTML += '<li class="salary"><strong>' + Resources.Updated + spacerStr + '</strong> ' + DateTime.fromJSDate(date2).toUTC().toFormat('yyyy-MM-dd - h:mm a') + '</li>';

                projectDetailsHTML += '<li class="salary"><strong>' + Resources.Rationale + spacerStr + '</strong> ' + (data.Results[i].Document.rationale) + '</li>';

            }
            projectDetailsHTML += '<li class="salary"><strong>' + Resources.ProjectPhase + spacerStr + '</strong> ' + (data.Results[i].Document.ea_phase) + '</li>';
            projectDetailsHTML += '<li class="salary"><strong>' + Resources.ParticipationNotice + spacerStr + '</strong> ' + (data.Results[i].Document.comment_pp_notice_title) + '</li>';

            //projectDetailsHTML += '<li class="salary"><strong>' + Resources.FileType + spacerStr + '</strong> ' + extension + '</li>';
            //projectDetailsHTML += '<li class="salary"><strong>' + "Document" + spacerStr + '</strong> ' + (fileName.split("/").pop() || "") + '</li>';
            projectDetailsHTML += '<li class="salary relevance_score"><strong>' + Resources.Relevance + spacerStr + '</strong> ' + (data.Results[i]["Score"].toFixed(4) * 100.0) + '</li>';

            var projectDesc = data.Results[i].Document.comment || "";
            if (projectDesc.indexOf(" ") == -1)
                projectDesc += " ";

            if (projectDesc.length > commentResultContentLength)
                projectDesc = projectDesc.substring(0, projectDesc.substring(0, commentResultContentLength).lastIndexOf(' ') + 1) + readMoreStr;

            projectDesc = '<li class="business">' + stripHTML(projectDesc); + '</li>';

            if (data.Results[i]["Highlights"] != null && data.Results[i]["Highlights"]["comment"] != null) {
                projectDesc = "";
                for (var y = 0; y < data.Results[i]["Highlights"].comment.length; y++) {
                    var highlightItem = removeUnicode(stripHTML(data.Results[i]["Highlights"].comment[y].toString()).replace(/___HighlightPreTag___/g, '<span class=\"bg-info\">').replace(/___HighlightPostTag___/g, '</span>'));
                    projectDesc += '<li class="business merged_result">' + highlightItem + '</li>';
                }
            }
            projectDetailsHTML += projectDesc;

            if (data.Results[i].Document.attached_count != null && data.Results[i].Document.attached_count > 0) {
                var attachmentCnt = data.Results[i].Document.attached_count;
                for (var x = 0; x < attachmentCnt; x++) {
                    var attachment = data.Results[i].Document.attachments[x];
                    var filename = attachment.metadata_storage_path.split("/").pop() || "";

                    //projectDetailsHTML += '<li class="salary document_name"><strong>Attachment'+ spacerStr + '</strong>' + filename + '</li>';
                    projectDetailsHTML += '<li class="salary document_name"><strong>' + Resources.AttachmentIncludedLbl + '</strong>' + '</li>';
                    projectDetailsHTML += '<li class="salary relevance_score"><strong>' + Resources.Relevance + spacerStr + '</strong> ' + (attachment.Score.toFixed(4) * 100.0) + '</li>';

                    var attachmentDesc = attachment.content || "";
                    if (attachmentDesc.indexOf(" ") == -1)
                        attachmentDesc += " ";

                    if (attachmentDesc.length > attachmentResultContentLength)
                        attachmentDesc = attachmentDesc.substring(0, attachmentDesc.substring(0, attachmentResultContentLength).lastIndexOf(' ') + 1) + readMoreStr;
                    attachmentDesc = '<li class="business merged_result">' + stripHTML(attachmentDesc) + '</li>';

                    if (attachment["Highlights"] != null && attachment["Highlights"]["content"] != null) {
                        attachmentDesc = "";
                        for (var y = 0; y < attachment["Highlights"]["content"].length; y++) {
                            var highlightItem = removeUnicode(stripHTML(attachment["Highlights"].content[y].toString()).replace(/___HighlightPreTag___/g, '<span class=\"bg-info\">').replace(/___HighlightPostTag___/g, '</span>'));
                            attachmentDesc += '<li class="business merged_result">' + highlightItem + '</li>';
                        }
                    }
                    projectDetailsHTML += attachmentDesc;
                }
            }

            projectDetailsHTML += '</ul></a>';

            //if (data.Results[i].Document.metadata_content_type != null && data.Results[i].Document.metadata_content_type.indexOf("text/html") >= 0)
            //{
            //    var downloadUrl = data.Results[i].Document.metadata_storage_path;
            //    projectDetailsHTML += '<a href="' + downloadUrl + '">' + '<ul class="list-unstyled"> <li>' + Resources.DownloadDocument + '</li></ul></a >';
            //}

            projectDetailsHTML += '</div></article>';
        }
        else if (data.Results[i].Document.document_type.indexOf("archive") !== -1) {

            var filePath = data.Results[i].Document.metadata_storage_path;
            var fileName = filePath.substring(filePath.lastIndexOf('/') + 1);
            var extension = fileName.substring(fileName.lastIndexOf('.') + 1).toUpperCase();

            if (data.Results[i].Document.document_type.indexOf("archive-project") !== -1) {
                projectDetailsHTML += '<article><a class="resultJobItem" href="' + 'https://iaac-aeic.gc.ca/archives/evaluations' + data.Results[i].Document.relative_path + '">';

                projectDetailsHTML += '<h3 class="title"><span class="job-source glyphicon glyphicon-globe"><span class="wb-inv">Project</span></span><span class="noctitle">' + data.Results[i].Document.project_name + Resources.archivedLbl +'</span></h3>';
                projectDetailsHTML += '<ul class="list-unstyled">';

                var locationLabel = "";
                for (var x = 0; x < data.Results[i].Document.location.length; x++) {
                    if (!isNullOrWhitespace(data.Results[i].Document.location[x])) {

                        if (x < data.Results[i].Document.province.length) {
                            locationLabel += " (" + data.Results[i].Document.location[x] + ", " + data.Results[i].Document.province[x] + ")";
                        }
                        else {
                            locationLabel += " (" + data.Results[i].Document.location[x] + ")";
                        }
                    }
                    else if (x < data.Results[i].Document.province.length && !isNullOrWhitespace(data.Results[i].Document.province[x])) {
                        locationLabel += " (" + data.Results[i].Document.province[x] + ")";
                    }
                }
                if (!isNullOrWhitespace(locationLabel)) {
                    projectDetailsHTML += '<li class="location"><span class="wb-inv">Location</span>';
                    projectDetailsHTML += locationLabel + '<br>' + '</li>';
                }
                var eaType = !(isNullOrWhitespace(data.Results[i].Document.ea_type)) ? data.Results[i].Document.ea_type : Resources.NoEaType;
                projectDetailsHTML += '<li class="salary"><strong>' + Resources.EaType + spacerStr + '</strong> ' + eaType;

                projectDetailsHTML += '<li class="salary"><strong>' + Resources.Status + spacerStr + '</strong> ' + data.Results[i].Document.status + '</li>';

                projectDetailsHTML += '<li class="salary"><strong>' + Resources.DocRefNum + spacerStr + '</strong> ' + (data.Results[i].Document.project_id) + '</li>';
                //projectDetailsHTML += '<li class="salary"><strong>' + Resources.Status + spacerStr + '</strong> ' + data.Results[i].Document.status + '</li>';
                //projectDetailsHTML += '<li class="salary"><strong>Document'+ spacerStr + '</strong> ' + fileName + '</li>';
                var date = new Date(parseInt(data.Results[i].Document.updated_at.substr(6)));

                projectDetailsHTML += '<li class="salary"><strong>' + Resources.Modified + spacerStr + '</strong> ' + date.toJSON().split('T')[0] + '</li>';
                projectDetailsHTML += '<li class="salary relevance_score"><strong>' + Resources.Relevance + spacerStr + '</strong> ' + (data.Results[i]["Score"].toFixed(4) * 100.0) + '</li>';

                var projectDesc = data.Results[i].Document.content || "";

                var test = projectDesc.indexOf("Please contact us to request a format other than those available.");
                if (test > 0) {
                    projectDesc = projectDesc.substring(test);
                }

                if (projectDesc.length > archiveResultContentLength)
                    projectDesc = projectDesc.substring(0, projectDesc.substring(0, archiveResultContentLength).lastIndexOf(' ') + 1) + readMoreStr;
                projectDesc = stripHTML(projectDesc);

                if (data.Results[i]["Highlights"] != null && data.Results[i]["Highlights"]["content"] != null)
                    projectDesc = (stripHTML(data.Results[i]["Highlights"].content).toString().replace(/___HighlightPreTag___/g, '<span class=\"bg-info\">').replace(/___HighlightPostTag___/g, '</span>'));

                projectDetailsHTML += '<li class="business">' + projectDesc + '</li>';
                projectDetailsHTML += '</ul>';
                projectDetailsHTML += '</a></article>';
            }
            else if (data.Results[i].Document.document_type.indexOf("archive-document") !== -1)
            {
                projectDetailsHTML += '<article><a class="resultJobItem" href="' + 'https://iaac-aeic.gc.ca/archives/evaluations' + data.Results[i].Document.relative_path + '">';

                projectDetailsHTML += '<h3 class="title"><span class="job-source glyphicon glyphicon-file"><span class="wb-inv">Document</span></span><span class="noctitle">' + decodeURIComponent(data.Results[i].Document.document_title.replace(/\+/g, '%20') + Resources.archivedLbl) + '</span></h3>';

                projectDetailsHTML += '<ul class="list-unstyled">';
                projectDetailsHTML += '<li class="location"><span class="wb-inv">Project</span>' + decodeURIComponent(data.Results[i].Document.project_name.replace(/\+/g, '%20') + Resources.archivedLbl) + '</li >';

                projectDetailsHTML += '<li class="salary"><strong>' + Resources.DocumentCategory + spacerStr + '</strong> ' + decodeURIComponent(data.Results[i].Document.document_category.replace(/\+/g, '%20')) + '</li>';

                projectDetailsHTML += '<li class="salary"><strong>' + Resources.DocRefNum + spacerStr + '</strong> ' + (data.Results[i].Document.project_id) + '</li>';

                var date = new Date(parseInt(data.Results[i].Document.updated_at.substr(6)));

                projectDetailsHTML += '<li class="salary"><strong>' + Resources.DocumentDate + spacerStr + '</strong> ' + date.toJSON().split('T')[0] + '</li>';
                projectDetailsHTML += '<li class="salary"><strong>Document'+ spacerStr + '</strong> ' + fileName + '</li>';
                projectDetailsHTML += '<li class="salary relevance_score"><strong>' + Resources.Relevance + spacerStr + '</strong> ' + (data.Results[i]["Score"].toFixed(4) * 100.0) + '</li>';

                var projectDesc = data.Results[i].Document.content || "";

                var test = projectDesc.indexOf("Please contact us to request a format other than those available.");
                if (test > 0) {
                    projectDesc = projectDesc.substring(test);
                }

                if (projectDesc.length > archiveResultContentLength)
                    projectDesc = projectDesc.substring(0, projectDesc.substring(0, archiveResultContentLength).lastIndexOf(' ') + 1) + readMoreStr;
                projectDesc = stripHTML(projectDesc);

                if (data.Results[i]["Highlights"] != null && data.Results[i]["Highlights"]["content"] != null)
                    projectDesc = (stripHTML(data.Results[i]["Highlights"].content).toString().replace(/___HighlightPreTag___/g, '<span class=\"bg-info\">').replace(/___HighlightPostTag___/g, '</span>'));

                projectDetailsHTML += '<li class="business">' + projectDesc + '</li>';
                projectDetailsHTML += '</ul>';
                projectDetailsHTML += '</a></article>';
            }

        }
    }
    $("#project_details_div").html(projectDetailsHTML);
    $("summary").trigger("wb-init.wb-details");
    $(".wb-tabs").trigger("wb-init.wb-tabs");
}

//jobbank scripts
//<![CDATA[
//Remove WET GC Theme Loupe Icon
$('#wb-glb-mn .overlay-lnk span.glyphicon.glyphicon-search').removeClass('glyphicon-search');
$('#results-filter-wrapper, .results-filter-content .list-group').addClass('noanim');
$('#results-filter-wrapper, .results-filter-content .list-group').each(function (i) {
    var elm = $(this);
    setTimeout(function () {
        elm.removeClass('noanim');
    }, i * 500);
});
//Initialize localstorage
var reload;
initlocalstorageFunctions = function () {
    if (localStorage) {
        if (localStorage.getItem('functionResultFilter') === 'active') {
            $('.skip-to-filters').show();
            //console.log('localstorage: filter is active');
            if ($('.results-filter-wrapper').length) {
                //console.log('Search results!');
                if ($('.results-filter-wrapper').css('visibility') === 'visible') {
                    reload = true;
                    //console.log('.results-filter-wrapper is VISIBLE');
                    //showFilter();
                    if ($('.search-input-content').css('display') === 'none') {
                        //console.log('display none - Mobile!');
                        hideFilter();
                    } else {
                        //console.log('display block - Desktop!');
                        showFilter();
                    }
                } else {
                    reload = true;
                    //console.log('.results-filter-wrapper is HIDDEN');
                    hideFilter();
                }
            }
            $('.results-list-wrapper').removeClass('col-md-12').addClass('col-md-9');
        } else if (localStorage.getItem('functionResultFilter') === 'disabled') {
            //console.log('functionResultFilter is disabled');
            reload = true;
            $('.skip-to-filters').hide();
            hideFilter();
        } else {
            reload = true;
            //console.log('localstorage: filter is N/A');
            showFilter();
            $('.results-list-wrapper').each(function (i) {
                var elm = $(this);
                setTimeout(function () {
                    elm.removeClass('noanim');
                }, i * 500);
            });
        }

        // Sort By
        if (localStorage.getItem('functionSortBy') === 'active') {
            //console.log('Sort By - Active');
            resetSearchOverlay();
            activateSortBy();
            if ($('.results-sortby-group').css('visibility') === 'hidden') {
                //Mobile
                if ($('.search-input-content-nav').css('display') === 'block') {
                    //console.log('Sort By - Mobile!');
                    if (!$('.results-sortby-group').hasClass('sortby-group-visible')) {
                        $('.results-filter-button-overlay').addClass('noBorder');
                        $('.results-sortby-group').addClass('sortby-group-visible');
                    }
                }
                //Desktop
                if ($('.search-input-content-nav').css('display') === 'none') {
                    //console.log('Sort By - Desktop!');
                    if ($('.results-sortby-group').hasClass('sortby-group-visible')) {
                        $('.results-filter-button-overlay').removeClass('noBorder');
                        $('.results-sortby-group').removeClass('sortby-group-visible');
                    }
                }
            } else if ($('.results-sortby-group').css('visibility') === 'visible') {
                //Mobile
                if ($('.search-input-content-nav').css('display') === 'block') {
                    //console.log('Sort By - Mobile!');
                    if (!$('.results-sortby-group').hasClass('sortby-group-visible')) {
                        $('.results-filter-button-overlay').addClass('noBorder');
                        $('.results-sortby-group').addClass('sortby-group-visible');
                    }
                }
                //Desktop
                if ($('.search-input-content-nav').css('display') === 'none') {
                    //console.log('Sort By - Desktop!');
                    $('main').removeClass('sortby-visible');
                    if ($('.results-sortby-group').hasClass('sortby-group-visible')) {
                        $('.results-filter-button-overlay').removeClass('noBorder');
                        $('.results-sortby-group').removeClass('sortby-group-visible');
                    }
                }
            }
        } else if (localStorage.getItem('functionSortBy') === 'disabled') {
            //console.log('Sort By - Disabled');
            $('main').removeClass('sortby-visible');
            $('.command-result-sortby-overlay').removeClass('active');
            //Mobile
            if ($('.search-input-content-nav').css('display') === 'block') {
                if ($('.results-sortby-group').hasClass('sortby-group-visible')) {
                    $('.results-filter-button-overlay').removeClass('noBorder');
                    $('.results-sortby-group').removeClass('sortby-group-visible');
                }
            }
            //Desktop
            if ($('.search-input-content-nav').css('display') === 'none') {
                if ($('.results-sortby-group').hasClass('sortby-group-visible')) {
                    $('.results-filter-button-overlay').removeClass('noBorder');
                    $('.results-sortby-group').removeClass('sortby-group-visible');
                }
            }
        } else {
            localStorage.setItem('functionSortBy', 'disabled');
            $('.results-filter-button-overlay').removeClass('noBorder');
            $('.results-sortby-group').removeClass('sortby-group-visible');
        }

        if ($('.results-content').hasClass('filter-hide')) {
            $("#results-filter-wrapper").addClass("invisible");
        } else
            if ($('.results-content').hasClass('filter-visible')) {
                $("#results-filter-wrapper").removeClass("invisible");
            }
    }
}
function resetSearchOverlay() {
    //console.log('Reset Search Overlay');
    $('main').removeClass('search-visible');
    $('.command-search-overlay').removeClass('active');
    $('.command-search-overlay').removeClass('btn-default');
    $('.command-search-overlay').addClass('btn-primary');
    $('.results-filter-button-overlay').removeClass('noBorder');
}
function activateSortBy() {
    //console.log('Activate Sort By Overlay');
    $('main').addClass('sortby-visible');
    localStorage.setItem('functionSortBy', 'active');
    $('.command-result-sortby-overlay').addClass('active');
    $('.results-sortby-group').addClass('sortby-group-visible');
    $('.results-filter-button-overlay').addClass('noBorder');
}
function resetSortBy() {
    //console.log('Reset Sort By Overlay');
    $('main').removeClass('sortby-visible');
    localStorage.setItem('functionSortBy', 'disabled');
    $('.command-result-sortby-overlay').removeClass('active');
    $('.results-sortby-group').removeClass('sortby-group-visible');
    $('.results-filter-button-overlay').removeClass('noBorder');
}
function hideFilter() {
    //console.log('Hide Filter');
    $('.command-result-filter-overlay').removeClass('active');
    $('.command-result-filter-overlay').html('<span class="fa fa-sliders-h" aria-hidden="true"></span> ' + Resources.DisplayFilters);
    $('.results-content').addClass('filter-hide').removeClass('filter-visible');

    if (reload) {
        //console.log('reload hide filter');
        //console.log('reload: '+reload);
        reload = false;
        $('.results-list-wrapper').removeClass('col-md-9').addClass('col-md-12 noanim');
    } else {
        //console.log('not reload hide filter');
        $('.results-list-wrapper').removeClass('noanim');
        $('.results-list-wrapper').removeClass('col-md-9').addClass('col-md-12');
    }
    localStorage.setItem('functionResultFilter', 'disabled');
}
function showFilter() {
    //console.log('Show Filter');
    $('.command-result-filter-overlay').removeClass('active');
    $('.command-result-filter-overlay').html('<span class="fa fa-sliders-h" aria-hidden="true"></span> ' + Resources.HideFilters);
    $('.results-content').addClass('filter-visible').removeClass('filter-hide');

    if (reload) {
        //console.log('reload show filter');
        reload = false;
        $('.results-list-wrapper').removeClass('col-md-12').addClass('col-md-9 noanim');
    } else {
        //console.log('not reload show filter');
        $('.results-list-wrapper').removeClass('noanim');
        $('.results-list-wrapper').removeClass('col-md-12').addClass('col-md-9');
    }
    localStorage.setItem('functionResultFilter', 'active');
}
//Initiate localstorage functions once document have been loaded
$(document).on("ready", initlocalstorageFunctions);

$(document).ready(function () {

    $('.results-content.filter-visible .results-filter-button-overlay').css('display', 'inline-block');
    $('.results-filter-button-overlay').show();
    $('.command-result-filter-overlay').addClass('active');

    if (localStorage) {
        if ($('.hero-content-wrapper').length) {
            localStorage.setItem('functionResultFilter', 'active');
        }
    }

    $('.command-advance-search').click(function () {
        $('.command-advance-search:first').toggleClass('active');
        $(this).stop().animate({ opacity: 1 }, 0, function () {
            $('html, body').animate({ scrollTop: $('.search-module').offset().top }, 'fast');
            $('#search-input-content').toggleClass('show-advance-search animated slideInDown');
        });
        return false;
    });

    //Advance search - language filter always associated with Job Bank jobs
    /*
    $('input[name="jobSearchForm:flg"]').change( function() {
        var langFlag = $('input[name="jobSearchForm:flg"]');
        if ($(langFlag).is(':checked')) {
            $('#jobSearchForm\\:fsrc\\:0').prop('checked',true);
        } else {
            $('#jobSearchForm\\:fsrc\\:0').prop('checked',false);
        }
    });
    */
    $('input[name="jobSearchForm:flg"]').change();

    $('#searchString').on('keyup blur focus change', function (e) {
        var searchStringValue = $(this).val();
        /* console.log('Search string value: '+keywords);
        $(this).val(keywords); */
        $('#searchStringForAdvanced').val(searchStringValue);
        //console.log('Advance search string value: '+$('#searchString_hidden').val());
    });
    $('#searchString').change();

    //$('#searchButton').click(function () {
    //    if ($(this).parents("section#search-input-content").hasClass("show-advance-search")) {
    //        //console.log('advance search');
    //        //alert('advance search');
    //        $('#searchButtonAdvance').click();
    //    } else {
    //        //console.log('normal search');
    //        //alert('normal search');
    //        return true;
    //    }
    //    return false;
    //});

    //Toggle checkbox for fper
    $('#jobSearchForm\\:fper input:checkbox').click(function () {
        var fper = $('#jobSearchForm\\:fper input:checkbox');
        var checked = $(this).is(':checked');

        fper.prop('checked', false);
        if (checked) {
            $(this).prop('checked', true);
        }
    });

    /* $('.tt-input').blur(function(event) {
          let menuLength = $('.tt-dataset-ta-communitysuggest > p').length
          if(event.keyCode == 13 && menuLength == 1) {
            $('.tt-dataset-ta-communitysuggest p:first-child').first()[0].click()
          }
    }); */

    $('.command-advance-search-clear').click(function () {
        $('#advance-search-group form').get(0).reset();
        $('#advance-search-group input[type=checkbox]').prop('checked', false);
        $('#advance-search-group input[type=radio]').prop('checked', false);
        $('#advance-search-group select').val("");
        $('#advance-search-group input[name=pcode').val("");
    });

    // Spotlight
    //$(".spotlight-tab header a").click(function () {
    //    $(this).parents(".spotlight-tab").toggleClass("open");

    //    if ($(this).parents(".spotlight-tab").hasClass("open")) {
    //        $(this).parents(".spotlight-tab").find(".container a.btn").removeAttr('tabindex');
    //        $(this).children(".arrowIndicator").removeClass("fa-angle-double-left");
    //        $(this).children(".arrowIndicator").addClass("fa-angle-double-right");
    //    } else {
    //        $(this).parents(".spotlight-tab").find(".container a.btn").attr('tabindex', '-1');
    //        $(this).children(".arrowIndicator").removeClass("fa-angle-double-right");
    //        $(this).children(".arrowIndicator").addClass("fa-angle-double-left");
    //    }
    //    return false;
    //});
    //$(document).click(function (e) {
    //    if (!$(e.target).parents().is('.spotlight-tab')) {
    //        $(".spotlight-tab").removeClass("open");
    //        $(".spotlight-tab").find(".container a.btn").attr('tabindex', '-1');
    //        $(".spotlight-tab").find(".arrowIndicator").removeClass("fa-angle-double-right");
    //        $(".spotlight-tab").find(".arrowIndicator").addClass("fa-angle-double-left");
    //    }
    //});
    //$(".featured-group a, .main-group a").hover(function () {
    //    //$(this).find('span.icon').toggleClass('slideInLeft animated');
    //    $(this).stop().animate({ opacity: 1 }, 0, function () {
    //        $(this).find('span.icon').toggleClass('animated pulse');
    //    });
    //    /* $(this).stop().animate({opacity:1}, 200, function(){
    //        $(this).find('span.task').toggleClass('animated fadeIn');
    //    }); */
    //});
    //$(".featured-tool a").hover(function () {
    //    $(this).stop().animate({ opacity: 1 }, 0, function () {
    //        $(this).find('.featured-tool-icon').toggleClass('animated bounceIn');
    //    });
    //});

    /* Store the window width */
    var windowWidth = $(window).width();
    var resizeUI;

    /* Resize Event */
    $(window).resize(function () {
        // Check window width has actually changed and it's not just iOS triggering a resize event on scroll
        if ($(window).width() != windowWidth) {

            // Update the window width for next time
            windowWidth = $(window).width();

            clearTimeout(resizeUI);
            resizeUI = setTimeout(resetUI, 400);
        }
    });

    //Remove Mobile Search Box
    //resetUI();
    function resetUI() {
        //Mobile
        if ($('.search-input-content-nav').css('display') === 'block') {
            //console.log('Mobile mode on!');
            //resetSearchOverlay();
            if (!$('main').hasClass('search-visible')) {
                resetSearchOverlay();
            }
            if (localStorage) {
                //Reset Filters no matter what
                if (localStorage.getItem('functionResultFilter') === 'active') {
                    //console.log('functionResultFilter ACTIVE');
                    $('.command-result-filter-overlay').removeClass('active');
                    $('.results-content').removeClass('filter-visible').addClass('filter-hide');
                    $('.command-result-filter-overlay').html('<span class="fa fa-sliders-h" aria-hidden="true"></span> ' + Resources.DisplayFilters);

                    localStorage.setItem('functionResultFilter', 'disabled');
                } else if (localStorage.getItem('functionResultFilter') === 'disabled') {
                    //console.log('functionResultFilter DISABLED');
                    $('.command-result-filter-overlay').removeClass('active');
                    $('.results-content').addClass('filter-hide').removeClass('filter-visible');
                    $('.command-result-filter-overlay').html('<span class="fa fa-sliders-h" aria-hidden="true"></span> ' + Resources.DisplayFilters);
                }

                // Sort by
                if (localStorage.getItem('functionSortBy') === null) {
                    //First time user
                    //console.log('sort null');
                    resetSortBy();
                } else {
                    if (localStorage.getItem('functionSortBy') === 'active') {
                        activateSortBy();
                        //console.log('sort active');
                    } else if (localStorage.getItem('functionSortBy') === 'disabled') {
                        if (!$('main').hasClass('search-visible')) {
                            resetSortBy();
                        }
                        //console.log('sort disabled');
                    }
                }
            }
            setTimeout(filterTaller, 300);
        }

        //Desktop
        if ($('.search-input-content-nav').css('display') === 'none') {
            //console.log('Desktop mode on!');
            if (localStorage) {
                if (localStorage.getItem('functionResultFilter') === null) {
                    //First time user
                    localStorage.setItem('functionResultFilter', 'active');
                    showFilter();
                } else {
                    //TODO - Verify if this was causing the Facet (FR) bug.
                    //if (localStorage.getItem('functionResultFilter') === 'active') {
                    //    //console.log('filter active!');
                    //    showFilter();
                    //} else if (localStorage.getItem('functionResultFilter') === 'disabled') {
                    //    //console.log('filter inactive!');
                    //    showFilter();
                    //}
                }
                // Sort by
                if (localStorage.getItem('functionSortBy') === null) {
                    //First time user
                    resetSortBy();
                } else {
                    if (localStorage.getItem('functionSortBy') === 'active') {
                        resetSortBy();
                    } else if (localStorage.getItem('functionSortBy') === 'disabled') {
                        resetSortBy();
                    }
                }
            } else {
                $('.results-content').addClass('filter-visible').removeClass('filter-hide');
                $('.results-list-wrapper').removeClass('col-md-12').addClass('col-md-9');
                // Sort by
                resetSortBy();
            }
            resetSortBy();
            resetSearchOverlay();
            setTimeout(filterTaller, 300);
            showFilter();
        }
        if ($('.results-content').hasClass('filter-hide')) {
            //console.log('filter-hide');
            $("#results-filter-wrapper").addClass("invisible");
        } else
            if ($('.results-content').hasClass('filter-visible')) {
                //console.log('filter-visible');
                $("#results-filter-wrapper").removeClass("invisible");
            }

    }

    //Mobile - Search Overlay Button
    $('.command-search-overlay').click(function (e) {
        //console.log('search mobile CLICK');
        $('main').toggleClass('search-visible');
        $('.command-search-overlay').toggleClass('active');
        $('.command-search-overlay').toggleClass('btn-primary btn-default');
        resetSortBy();

        if ($('main').hasClass("search-visible")) {
            $('.results-filter-button-overlay').addClass('noBorder');
            //console.log('search mobile SHOW!');
        } else {
            $('.results-filter-button-overlay').removeClass('noBorder');
            //console.log('search mobile HIDE!');
        }
        //$('html, body').animate({ scrollTop: $('.search-input-content').offset().top }, '500');
        //e.preventDefault();
    });

    //Activate Filter
    $('.command-result-filter-overlay').click(function () {
        resetSearchOverlay();
        resetSortBy();
        $('.results-content').toggleClass('filter-visible filter-hide');
        $('.command-result-filter-overlay').toggleClass('active');

        if ($('.command-result-sortby-overlay').hasClass("active")) {
            $('.results-filter-button-overlay').addClass('noBorder');
        } else {
            $('.results-filter-button-overlay').removeClass('noBorder');
        }
        if ($('.results-content').hasClass('filter-visible')) {
            //console.log('Display Filter!');
            $('.skip-to-filters').show();
            $('.command-result-filter-overlay').html('<span class="fa fa-sliders-h" aria-hidden="true"></span> ' + Resources.HideFilters);
            if ($('.search-input-content-nav').css('display') === 'block') {
                if ($(this).parent('.results-filter-button-overlay')) {
                    //console.log('mobile go to filter top');
                    $('html, body').animate({ scrollTop: $('.results-filter-content').offset().top }, 'fast');
                }
            }
            if (localStorage) {
                //console.log('LS functionResultFilter active');
                localStorage.setItem('functionResultFilter', 'active');
            }
        } else if ($('.results-content').hasClass('filter-hide')) {
            //console.log('Hide Filter!');
            $('.command-result-filter-overlay').html('<span class="fa fa-sliders-h" aria-hidden="true"></span> ' + Resources.DisplayFilters);
            $('.skip-to-filters').hide();
            if ($('.search-input-content-nav').css('display') === 'block') {
                if ($(this).parent('.results-filter-button-overlay')) {
                    //console.log('mobile go to result top');
                    $('html, body').animate({ scrollTop: $('#results-list-content').offset().top }, 'fast');
                }
            }
            if (localStorage) {
                //console.log('LS functionResultFilter disabled');
                localStorage.setItem('functionResultFilter', 'disabled');
            }
        }

        setTimeout(function () {
            if ($('.results-content').hasClass('filter-hide')) {
                $("#results-filter-wrapper").addClass("invisible");
            } else if ($('.results-content').hasClass('filter-visible')) {
                $("#results-filter-wrapper").removeClass("invisible");
            }
        }, 200);
        $('.results-list-wrapper').removeClass('noanim');
        $('.results-list-wrapper').toggleClass('col-md-12 col-md-9');

        setTimeout(filterTaller, 300);
    });

    //Activate Show Map
    $('#show-map-button').click(function () {
        if ($('#show-map-button').hasClass("active")) {
            ShowMap();

            if ($('.search-input-content-nav').css('display') === 'block') {
                if ($(this).parent('.results-filter-button-overlay')) {
                    //console.log('mobile go to map top');
                    $('html, body').animate({ scrollTop: $('#map-wrapper').offset().top }, 'fast');
                }
            }
        } else {
            HideMap();
        }
    });

    //Activate Sort By
    $('.command-result-sortby-overlay').click(function () {
        resetSearchOverlay();

        $('main').toggleClass('sortby-visible');
        $('.command-result-sortby-overlay').toggleClass('active');
        if ($('.command-result-sortby-overlay').hasClass("active")) {
            if ($('.results-sortby-group').css('display') === 'none') {
                //console.log('.results-sortby-group is currently hidden');
                //console.log('.results-sortby-group SHOW!');
                localStorage.setItem('functionSortBy', 'active');
                $('.results-filter-button-overlay').addClass('noBorder');
                $('.results-sortby-group').addClass('sortby-group-visible');
            }
        } else {
            if ($('.results-sortby-group').css('display') === 'block') {
                //console.log('.results-sortby-group HIDE!');
                localStorage.setItem('functionSortBy', 'disabled');
                $('.results-filter-button-overlay').removeClass('noBorder');
                $('.results-sortby-group').removeClass('sortby-group-visible');
            }
        }
    });

    $('.results-sortby-group a.btn').click(function () {
        localStorage.setItem('functionSortBy', 'disabled');
    });

    $('.overlay').click(function () {
        if ($(this).css('visibility') === 'visible') {
            resetSearchOverlay();
            resetSortBy();
        }
    });

    //Toggle Filter List - Check if filter list is visible or hidden
    var filterNum = 0;
    function checkToggleFilterList() {

        var allids = [];
        //$('div.results-filter-content section').find('ul.list-group').hide();
        $('div.results-filter-content section').find('.list-group').addClass('close');
        $('div.results-filter-content section h3').attr({ "tabindex": "0", "aria-expanded": "true", "aria-haspopup": "true", "data-toggle": "dropdown" }).remove('.toggleFilterList').append(' <span class="toggleFilterList"><span class="fa fa-plus" aria-hidden="true"></span><span class="wb-inv"> Filters </span></span>');
        var hasLooped = false;

        //Generate IDs for Filter List sections
        if (!hasLooped) {
            $('div.results-filter-content section').each(function () {

                //console.log('how many categories?');
                filterNum++;
                var newID = 'filterList' + filterNum;
                $(this).attr('id', newID);
                $(this).val(filterNum);

                //Set local storage
                if ($(this).children('h3').attr('aria-expanded') == 'true') {
                    var ids = $(this).map(function () { return this.id; }).get().join();
                    allids.push(ids);
                    //console.log('open: '+JSON.stringify(allids));
                    if (localStorage) {
                        localStorage.setItem("open", JSON.stringify(allids));
                    }
                } else if ($(this).children('h3').attr('aria-expanded') == 'false') {
                    var ids = $(this).map(function () { return this.id; }).get().join();
                    allids.push(ids);
                    //console.log('open: '+JSON.stringify(allids));
                    if (localStorage) {
                        localStorage.removeItem("remove", JSON.stringify(allids));
                    }
                }
                if (localStorage) {
                    if (localStorage.getItem('open') === null) {
                        //console.log('First time user');
                        allids = [];
                        var defaultListFilter = ['filterList1'];
                        localStorage.setItem('open', JSON.stringify(defaultListFilter));

                        if ($('#' + defaultListFilter.join(', #')).find('.list-group').hasClass('close')) {
                            $(this).find('.list-group').toggleClass('close open');
                            $(this).find('h3').attr({ "tabindex": "0", "aria-expanded": "true", "aria-haspopup": "true", "data-toggle": "dropdown" }).find('.toggleFilterList').html(' <span class="fa fa-minus" aria-hidden="true"></span><span class="wb-inv"> Hide filters</span>');

                        }
                    } else {
                        var openFilterList = localStorage.getItem("open");
                        openFilterListId = jQuery.parseJSON(openFilterList);
                        openFilters = $('#' + openFilterListId.join(', #'));

                        if ($(openFilters).find('.list-group').hasClass('close')) {
                            $(this).find('.list-group').toggleClass('close open');
                        }
                        if ($(openFilters).find('.list-group').hasClass('open')) {
                            if ($(openFilters).find('h3').has('span.fa.fa-plus').length) {
                                $(this).find('h3').attr({ "tabindex": "0", "aria-expanded": "true", "aria-haspopup": "true", "data-toggle": "dropdown" }).find('.toggleFilterList').html(' <span class="fa fa-minus" aria-hidden="true"></span><span class="wb-inv"> Hide filters</span>');
                            }
                        }
                        hasLooped = true;
                    }
                } else {
                    //console.log('no localstorage');
                    allids = [];
                    var defaultListFilter = ['filterList1', 'filterList2', 'filterList3', 'filterList4', 'filterList5', 'filterList6', 'filterList7', 'filterList8', 'filterList9', 'filterList10', 'filterList11', 'filterList12', 'filterList13'];

                    if ($('#' + defaultListFilter.join(', #')).find('.list-group').hasClass('close')) {
                        $(this).find('.list-group').toggleClass('close open');
                        $(this).find('h3').attr({ "tabindex": "0", "aria-expanded": "true", "aria-haspopup": "true", "data-toggle": "dropdown" }).find('.toggleFilterList').html(' <span class="fa fa-minus" aria-hidden="true"></span><span class="wb-inv">Hide filters</span>');
                    }
                }

            });


        }

    }
    checkToggleFilterList();

    //Toggle Filter List - Click function
    $('div.results-filter-content section h3').click(function (event) {
        toggleFilterList($(this));


    });
    //Toggle Filter List - Keyboard function
    $('div.results-filter-content section h3').keydown(function (event) {
        // Enter key
        if (event.keyCode == 13) {
            toggleFilterList($(this));
        }
        setTimeout(filterTaller, 0);
    });

    //Toggle Filter List - Function
    function toggleFilterList(thisObj) {
        var allids = [];
        //thisObj.closest('section').find('ul.list-group').toggle();
        if (thisObj.closest('section').find('.list-group').hasClass('open')) {
            //console.log('close it!');
            thisObj.closest('section').find('.list-group').toggleClass('open close');
        } else if (thisObj.closest('section').find('.list-group').hasClass('close')) {
            //console.log('open it!');
            thisObj.closest('section').find('.list-group').toggleClass('close open');
        } else {
            //console.log('open it anyways!');
            thisObj.closest('section').find('.list-group').addClass('open');
        }
        //filterTaller;
        setTimeout(filterTaller, 300);

        //Hidden
        //if (thisObj.closest('section').find('ul.list-group').is(':hidden')) {
        if (thisObj.closest('section').find('.list-group').hasClass('close')) {
            thisObj.attr({
                "aria-expanded": "false"
            });
            thisObj.find('span.toggleFilterList').html(' <span class="fa fa-plus" aria-hidden="true"></span><span class="wb-inv">Display Filters</span>');

            var filterSectionId = thisObj.parent().attr('id');
            //console.log('You closed: '+filterSectionId);
            if (localStorage) {
                if (!localStorage.getItem("open")) {
                    localStorage.setItem("open", "[]");
                }

                var allids = JSON.parse(localStorage.getItem('open'));

                for (i = 0; i < allids.length; i++)
                    if (allids[i] == filterSectionId) allids.splice(i, 1);
                localStorage["open"] = JSON.stringify(allids);
                //console.log('Current Open Set!: '+JSON.stringify(allids));
            }
        }
        //Visible
        //if (thisObj.closest('section').find('ul.list-group').is(':visible')) {
        if (thisObj.closest('section').find('.list-group').hasClass('open')) {
            thisObj.attr({
                "aria-expanded": "true"
            });
            thisObj.find('span.toggleFilterList').html(' <span class="fa fa-minus" aria-hidden="true"></span><span class="wb-inv"> Hide Filters</span>');

            var filterSectionId = thisObj.parent().attr('id');
            //console.log('You opened: '+filterSectionId);

            if (localStorage) {
                if (localStorage.getItem('open') === null) {
                    allids = [];
                } else {
                    if (!localStorage.getItem("open")) {
                        localStorage.setItem("open", "[]");
                    }
                    allids = JSON.parse(localStorage.getItem('open'));
                }
            }
            var exist = false;
            for (var i = 0; i < allids.length; i++)
                if (allids[i] == filterSectionId) {
                    exist = true;
                    break;
                }
            if (!exist) {
                allids.push(filterSectionId);
                if (localStorage) {
                    localStorage.setItem('open', JSON.stringify(allids));
                    //console.log('Current Open Set: '+JSON.stringify(allids));
                }
            } else {
                return false;
            }
        }
    }



    setTimeout(filterTaller, 300);

    //Reset for Input Ranger Slider
    //$('#jobSearchResultsJobSearchForm').submit(function () {
    //    if (localStorage) {
    //        localStorage.setItem('functionSearchSubmit', 'true');
    //    }
    //});

    //Input Ranger Slider Ouput Events
    if (localStorage) {
        if (!localStorage.getItem("functionRangeSliderOuputValue")) {
            var id, val;
        } else {
            if (!localStorage.getItem("functionSearchSubmit")) {
                //var id = localStorage.getItem('functionRangeSliderOuputID');
                //var val = localStorage.getItem('functionRangeSliderOuputValue');
                //$('#'+id).val(val);
                //Rely on JSF param
                var id, val;
            } else {
                if (localStorage.getItem("functionSearchSubmit") === 'true') {
                    localStorage.removeItem("functionRangeSliderOuputValue");
                    localStorage.removeItem("functionSearchSubmit");
                }
            }
        }
    }


    //Input Range event
    $("input[type='range']").on('input change', function (e) {
        /* var as1 = $(e.target).attr('data-sign1');
        var as2 = $(e.target).attr('data-sign2'); */
        var id = $(e.target).attr('id');
        var form = $(e.target).parents('form:first');
        var output = form.find('.output');
        var value = parseFloat($(e.target).val());
        updateRangeSliderOuput(output, id, value);
        //console.log('range input change!');
        //alert('range input change!');
    });
    $("input[type='range']").change();

    /* $("input[type='range']").on('keypress',function(e) {
        var id1 = $(e.target).attr('id');
        var val1 = $(e.target).val();
        //alert(val1);
        updateRangeSliderOuput(id1,val1);
    });
    $("input[type='range']").change(); */

    //var timeoutHandler = window.setTimeout(function () { ; }, 1);

    //$('a.decrease.range-slider-button').click(function (e) {
    //    var form = $(e.target).parents('form:first');
    //    var output = form.find('.output');
    //    var slider = form.find("input[type='range']");
    //    var step = parseFloat(slider.attr('step'));
    //    var minvalue = parseInt(slider.attr('min'));
    //    var value = parseFloat(slider.val());
    //    value = value - step
    //    if (value < minvalue) {
    //        value = minvalue;
    //    }
    //    slider.val(value);
    //    updateRangeSliderOuput(output, slider.attr('id'), value);
    //    //slider.change();

    //    window.clearTimeout(timeoutHandler);
    //    timeoutHandler = setTimeout(function () {
    //        form.submit();
    //        //slider.focus();
    //    }, 2000);
    //});

    //$('a.increase.range-slider-button').click(function (e) {
    //    var form = $(e.target).parents('form:first');
    //    var output = form.find('.output');
    //    var slider = form.find("input[type='range']");
    //    var step = parseFloat(slider.attr('step'));
    //    var maxvalue = parseInt(slider.attr('max'));
    //    var value = parseFloat(slider.val());
    //    value = value + step
    //    if (value > maxvalue) {
    //        value = maxvalue;
    //    }
    //    slider.val(value);
    //    updateRangeSliderOuput(output, slider.attr('id'), value);
    //    //slider.change();

    //    window.clearTimeout(timeoutHandler);
    //    timeoutHandler = setTimeout(function () {
    //        form.submit();
    //        //slider.focus();
    //    }, 2000);

    //});

    ////Input Range Slider function
    //function updateRangeSliderOuput(output, id, val) {
    //    //console.log('slider function');
    //    var value, label, details;
    //    //alert("ID " + id + " Value " + val);
    //    //Distance radius control
    //    if (id === "dist") {
    //        var details = '<span class="wb-inv">kilometers: selected distance</span>';
    //        var label = '<span class="wb-inv">Current distance of </span>';
    //        var value = '<span>' + val.toLocaleString('en-CA') + '</span>';
    //        //var display_value = '<span aria-hidden=\'true\'>'+val+'</span>';
    //    } /* else if (id === "salary") {
    //    var details = '<span class="wb-inv">thousand dollars is chosen</span>';
    //    var label = '<span class="wb-inv">Current annual salary of</span>';
    //} */
    //    if (localStorage) {
    //        //console.log('Function SAVED the values!');
    //        localStorage.setItem('functionRangeSliderOuputValue', val);
    //        localStorage.setItem('functionRangeSliderOuputID', id);

    //    }
    //    //console.log('value: '+val);
    //    //Update display label
    //    //$('span[class="output amount-dist"]').html(value);
    //    output.text(val.toLocaleString('en-CA'));
    //}

    //$('input[type=range]').on('mouseup touchend', function (e) {
    //    var form = $(e.target).parents('form');
    //    window.clearTimeout(timeoutHandler);
    //    timeoutHandler = setTimeout(function () {
    //        form.submit();
    //    }, 1000);
    //});
    //$('input[type=range]').on('keyup', function (e) {
    //    var key = e.which;
    //    // Enter key
    //    if ((key == 13)) {
    //        $(e.target).parents('form').submit();
    //        return false;
    //    }
    //    return false;
    //});

    //Floating label
    $('.float-input').on('focus blur change', function (e) {
        $(this).parents('.related-group').prev('label.control-label').find('.label').removeClass('focus-error').toggleClass('focus', (e.type === 'focus' || this.value.length > 0));
    }).trigger('focus blur change');
    $('.float-input').change();

    //event tracking for search
    //$('#jobSearchForm').submit(function (e) {
    //    var label = [];
    //    console.log(label);

    //    //check what the advanced search is about
    //    if ($("#searchString").val()) label.push("Keyword");
    //    if ($("#pcode").val()) label.push("Job Number");

    //    var flg = document.getElementsByName('jobSearchForm:flg');
    //    for (var i = 0, length = flg.length; i < length; i++) {
    //        if (flg[i].checked) {
    //            label.push("Language");
    //            break;
    //        }
    //    }

    //    var fper = document.getElementsByName("jobSearchForm:fper");
    //    for (var i = 0, length = fper.length; i < length; i++) {
    //        if (fper[i].checked) {
    //            label.push("Period of Employment");
    //            break;
    //        }
    //    }

    //    var fter = document.getElementsByName("jobSearchForm:fter");
    //    for (var i = 0, length = fter.length; i < length; i++) {
    //        if (fter[i].checked) {
    //            label.push("Job Type");
    //            break;
    //        }
    //    }

    //    var fss = document.getElementsByName("jobSearchForm:fss");
    //    for (var i = 0, length = fss.length; i < length; i++) {
    //        if (fss[i].checked) {
    //            label.push("Education Level");
    //            break;
    //        }
    //    }

    //    var fsrc = document.getElementsByName('jobSearchForm:fsrc');
    //    for (var i = 0, length = fsrc.length; i < length; i++) {
    //        if (fsrc[i].checked) {
    //            label.push("Federal Jobs Filter");
    //            break;
    //        }
    //    }

    //    var fjsf = document.getElementsByName('jobSearchForm:fjsf');
    //    if (fjsf[0].checked) label.push("Student Job Filter");

    //    var fet = document.getElementsByName('jobSearchForm:fet');
    //    if (fet[0].checked) label.push("Non-Placement Agency Filter");

    //    var fgff = document.getElementsByName('jobSearchForm:fgff');
    //    if (fgff[0].checked) label.push("Government Funded Jobs Filter");

    //    var fprov = document.getElementsByName("jobSearchForm:fprov");
    //    for (var i = 0, length = fprov.length; i < length; i++) {
    //        if (fprov[i].checked) {
    //            label.push("PTs and Regions");
    //            break;
    //        }
    //    }

    //    var fcat = document.getElementsByName("jobSearchForm:fcat");
    //    for (var i = 0, length = fcat.length; i < length; i++) {
    //        if (fcat[i].checked) {
    //            label.push("Job Categories");
    //            break;
    //        }
    //    }

    //    if ($("select[name=fn]").val()) label.push("Job Titles");

    //    //format result (always +',' to keep things as they are since the error was made at the begining...)
    //    var results = '';
    //    for (var i = 0, len = label.length; i < len; i++) {
    //        results += label[i] + ', ';
    //    }

    //    //push event
    //    _gaq.push(['_trackEvent', 'jobSearch', 'source : advancedSearchPage', results]);
    //    //console.log(results);
    //});

    // Economic Regions list is hidden by default
    $(".geoarea_list").hide();

    // Show Economic Regions belonging to a P/T when this P/T is select
    $('input.select-pt').change(function () {
        if ($(this).is(':checked')) {
            //console.log('Checked Province');
            $(this).parent().find('.geoarea_list').show();
            $(this).next('label').children('i').addClass('fa-minus-square').removeClass('fa-plus-square');
            if ($(this).parent().find('.geoarea_list').find('input[id^="box-fgeo-"]').is(':checked')) {
                $(this).prop('checked', true);
                $(this).parent().find('.geoarea_list').find('input[id^="box-fgeo-"]').prop('checked', false);
            }
        } else {
            //console.log('Unchecked Province');
            $(this).parent().find('.geoarea_list').hide();
            $(this).next('label').children('i').addClass('fa-plus-square').removeClass('fa-minus-square');
            if ($(this).parent().find('.geoarea_list').find('input[id^="box-fgeo-"]').is(':checked')) {
                //console.log('Cities are already checked!');
                $(this).prop('checked', false);
                //console.log('Uncheck province!');
            }
        }
    });

    // Uncheck P/T when a Economic Region inside the P/T is selected
    $('input[id^="box-fgeo-"]').change(function () {
        //console.log('Cities Checked then Unchecked Province');
        $(this).parents('.geoarea_list').parent().find('input.select-pt').prop('checked', false);
    });
    var itself;
    $('.btn-apply').click(function () {
        externalJobLink();
        $('#external-job-show').addClass('hide');
        //var itself = false;
    });
    //Apply
    $('#external-job-show').click(function () {
        var itself = true;
        externalJobLink();
        $('#external-job-show').addClass('hide');
        return false;
    });
    /* function externalJobLink() {
        if (!itself == true) {
            $('#external-job-details').attr('open','');
        }

        $('#externalJobLink').animate({opacity:1}, 0, function(){
            $(this).addClass('animated bounceIn');
            setTimeout(function(){
                $('#externalJobLink').focus();
                }, 900);
        });
    } */
    /* Uh new Firefox supports details :O */
    $('details summary').click(function () {
        setTimeout(filterTaller, 0);
    });
});

function filterTaller() {
    var filterBox = $('.results-filter-wrapper').height();
    var resultBox = $('.results-list-content').height();

    if ($('.search-input-content').css('display') === 'none') {
        //console.log('filterTaller display none - Mobile!');
        $('section.results-content').css('height', 'auto');
    } else {
        //console.log('filterTaller display block - Desktop!');
        if ($('section.results-content').hasClass('filter-visible')) {
            if ($('.search-input-content-nav').css('display') === 'none') {
                if (filterBox > resultBox) {
                    //console.log('filter box is taller: '+filterBox);
                    $('section.results-content').height(filterBox);
                }
            }
            if (resultBox > filterBox) {
                //console.log('result box is taller: '+resultBox);
                $('section.results-content').css('height', 'auto');
            }
        } else if ($('section.results-content').hasClass('filter-hide')) {
            //console.log('no filter box');
            $('section.results-content').css('height', 'auto');
        }
    }

}
$(document).on("wb-ready.wb-details", "summary", function (event) {
    $('details summary').click(function () {
        setTimeout(filterTaller, 0);
    });
    function filterTaller() {
        var filterBox = $('.results-filter-wrapper').height();
        var resultBox = $('.results-list-content').height();

        if ($('section.results-content').hasClass('filter-visible')) {
            if ($('.search-input-content-nav').css('display') === 'none') {
                if (filterBox > resultBox) {
                    //console.log('filter box is taller: '+filterBox);
                    $('section.results-content').height(filterBox);
                }
            }
            if (resultBox > filterBox) {
                //console.log('result box is taller: '+resultBox);
                $('section.results-content').css('height', 'auto');
            }
        } else if ($('section.results-content').hasClass('filter-hide')) {
            //console.log('no filter box');
            $('section.results-content').css('height', 'auto');
        }
    }
    setTimeout(filterTaller, 300);

});