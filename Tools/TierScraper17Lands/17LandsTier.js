const ratingsDict = {"grid-row: 16 / auto;":0.0, //"TBD"
                     "grid-row: 15 / auto;":0.0, //"SB"
                     "grid-row: 14 / auto;":0.4, //"F"
                     "grid-row: 13 / auto;":0.8, //"D-" 
                     "grid-row: 12 / auto;":1.2, //"D"
                     "grid-row: 11 / auto;":1.5, //"D+"
                     "grid-row: 10 / auto;":1.9, //"C-"
                     "grid-row: 9 / auto;":2.3,  //"C"
                     "grid-row: 8 / auto;":2.7,  //"C+"
                     "grid-row: 7 / auto;":3.1,  //"B-"
                     "grid-row: 6 / auto;":3.5,  //"B"
                     "grid-row: 5 / auto;":3.8,  //"B+"
                     "grid-row: 4 / auto;":4.2,  //"A-"
                     "grid-row: 3 / auto;":4.6,  //"A"
                     "grid-row: 2 / auto;":5.0}  //"A+"
const columnPrefix = "tier_text tier_bucket shared "
const colorIds = ["W","U","B","R","G","M","C","L"]

window.addEventListener('load', function () {
        var grid_zone = document.getElementById("sortable_card_tiers_app")
        var tier_button = document.createElement("button");
        
        tier_button.setAttribute("id", "tier_button")
        tier_button.innerHTML = "Download Tier List";
        grid_zone.insertBefore(tier_button, grid_zone.firstElementChild);
        
        document.getElementById("tier_button").addEventListener("click", CollectPickRatings);

})

function CollectPickRatings (){
    var currentdate = new Date(); 
    var datetime = (currentdate.getMonth()+1)  + "/"
                 + currentdate.getDate() + "/" 
                 + currentdate.getFullYear() + " "
                 + currentdate.getHours() + ":"  
                 + currentdate.getMinutes() + ":" 
                 + currentdate.getSeconds();
    
    var ratingsObj = new Object;
    var tierLabel = CollectLabel();
    var setName = CollectSetName();
    ratingsObj.meta = {"collection_date": datetime, "label": tierLabel, "set": setName, "version": 1.0};
    ratingsObj.ratings = {}
    
    for (var i = 0; i < colorIds.length; i++)
    {
        ratingsObj = CollectColumnRatings(colorIds[i], ratingsObj);
    }
        
    RatingsExport (ratingsObj);
}

function CollectColumnRatings (columnId, ratingsObj){

    var columnString = columnPrefix + columnId;
	var tableRows = document.getElementsByClassName(columnString);
    
    for(let i = 0; i < tableRows.length; i++)
    {
        let rowRating = ratingsDict[tableRows[i].getAttribute("style")];
        
        //Iterate through the columns and check for an items
        let tableItems = tableRows[i].getElementsByClassName("tier_card_name");
        
        //Iterate through the items in this column
        for(let j = 0; j < tableItems.length; j++)
        {
            let cardName = tableItems[j].innerHTML;
            ratingsObj.ratings[cardName] = rowRating;
        }
    }
    
    
    return ratingsObj;
}

function CollectSetName (){
    var setName = "";
    
    try{
        let tierListElement = document.getElementById("sortable_card_tiers_app");
        
        setName = tierListElement.dataset.expansion;
    
    }catch(error){
        console.log(error);
    }
    
    return setName;
}

function CollectLabel (){
    var tierLabel = "";
    
    try{
        tierLabel = document.querySelector("h2").textContent;
    }catch(error){
        console.log(error);
    }
    
    return tierLabel;
}
function RatingsExport (ratingsObj){

	var url = document.URL.split("/");

    var filename = `Tier_${ratingsObj.meta.set}_${Date.now().toString()}.txt`
	
	var _ratingObj = JSON.stringify(ratingsObj , null, 4); //indentation in json format, human readable
	
	var vLink = document.createElement('a'),
	vBlob = new Blob([_ratingObj], {type: "octet/stream"}),
	vName = filename;
	vUrl = window.URL.createObjectURL(vBlob);
	vLink.setAttribute('href', vUrl);
	vLink.setAttribute('download', vName );
	vLink.click();
}

