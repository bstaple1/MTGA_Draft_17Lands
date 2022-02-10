//var ratingsDict = {"TBD":0.0,"SB":0.0,"F":0.4,"D-":0.8,"D":1.2,"D+":1.5,"C-":1.9,"C":2.3,"C+":2.7,"B-":3.1,"B":3.5,"B+":3.8,"A-":4.2,"A":4.6,"A+":5.0}
const ratingsDict = {"grid-row: 16 / auto;":0.0,"grid-row: 15 / auto;":0.0,"grid-row: 14 / auto;":0.4,"grid-row: 13 / auto;":0.8,"grid-row: 12 / auto;":1.2,"grid-row: 11 / auto;":1.5,"grid-row: 10 / auto;":1.9,"grid-row: 9 / auto;":2.3,"grid-row: 8 / auto;":2.7,"grid-row: 7 / auto;":3.1,"grid-row: 6 / auto;":3.5,"grid-row: 5 / auto;":3.8,"grid-row: 4 / auto;":4.2,"grid-row: 3 / auto;":4.6,"grid-row: 2 / auto;":5.0}
        

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
    ratingsObj.meta = {"collection_date": datetime, "label":"", "set":"", "version": 1.0};
    ratingsObj.ratings = {}
    ratingsObj = CollectColumnRatings("tier_text tier_bucket shared W", ratingsObj);
    
    ratingsObj = CollectColumnRatings("tier_text tier_bucket shared U", ratingsObj);
    
    ratingsObj = CollectColumnRatings("tier_text tier_bucket shared B", ratingsObj);
	
    ratingsObj = CollectColumnRatings("tier_text tier_bucket shared R", ratingsObj);
    
    ratingsObj = CollectColumnRatings("tier_text tier_bucket shared G", ratingsObj);
    
    ratingsObj = CollectColumnRatings("tier_text tier_bucket shared M", ratingsObj);
    
    ratingsObj = CollectColumnRatings("tier_text tier_bucket shared C", ratingsObj);
    
    ratingsObj = CollectColumnRatings("tier_text tier_bucket shared L", ratingsObj);
        
    RatingsExport (ratingsObj);
}

function CollectColumnRatings (columnString, ratingsObj){

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

function RatingsExport (ratingsObj){

	var url = document.URL.split("/");

	var fileName = "Tier_" +  Date.now().toString() + ".json";
	
	var _ratingObj = JSON.stringify(ratingsObj , null, 4); //indentation in json format, human readable
	
	var vLink = document.createElement('a'),
	vBlob = new Blob([_ratingObj], {type: "octet/stream"}),
	vName = fileName;
	vUrl = window.URL.createObjectURL(vBlob);
	vLink.setAttribute('href', vUrl);
	vLink.setAttribute('download', vName );
	vLink.click();
}

