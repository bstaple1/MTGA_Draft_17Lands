const ratings_dict = {"grid-row: 16 / auto;":"NA", //"TBD"
                     "grid-row: 15 / auto;":"NA", //"SB"
                     "grid-row: 14 / auto;":"F ", //"F"
                     "grid-row: 13 / auto;":"D-", //"D-" 
                     "grid-row: 12 / auto;":"D ", //"D"
                     "grid-row: 11 / auto;":"D+", //"D+"
                     "grid-row: 10 / auto;":"C-", //"C-"
                     "grid-row: 9 / auto;" :"C ",  //"C"
                     "grid-row: 8 / auto;" :"C+",  //"C+"
                     "grid-row: 7 / auto;" :"B-",  //"B-"
                     "grid-row: 6 / auto;" :"B ",  //"B"
                     "grid-row: 5 / auto;" :"B+",  //"B+"
                     "grid-row: 4 / auto;" :"A-",  //"A-"
                     "grid-row: 3 / auto;" :"A ",  //"A"
                     "grid-row: 2 / auto;" :"A+"}  //"A+"
const column_prefix = "tier_text tier_bucket shared "
const color_ids = ["W","U","B","R","G","M","C","L"]

window.addEventListener('load', function () {
        var grid_zone = document.getElementById("sortable_card_tiers_app")
        var tier_button = document.createElement("button");
        var tier_label_box = document.createElement("textarea");
        var label_div = document.createElement("div")
        var button_div = document.createElement("div")
        
        tier_button.setAttribute("id", "tier_button")
        tier_button.innerHTML = "Download Tier List";
        
        tier_label_box.setAttribute("id", "tier_label_box")
        tier_label_box.setAttribute("rows", 1)
        tier_label_box.setAttribute("spellcheck", false)
        tier_label_box.setAttribute("placeholder", "Enter Label Here!")
        
        label_div.appendChild(tier_label_box)
        button_div.appendChild(tier_button)
        
        grid_zone.insertBefore(button_div, grid_zone.firstElementChild);
        grid_zone.insertBefore(label_div, grid_zone.firstElementChild);
        
        document.getElementById("tier_button").addEventListener("click", collect_pick_ratings);

})

function collect_pick_ratings (){
    var current_date = new Date(); 
    var datetime = (current_date.getMonth()+1)  + "/"
                 + current_date.getDate() + "/" 
                 + current_date.getFullYear() + " "
                 + current_date.getHours() + ":"  
                 + current_date.getMinutes() + ":" 
                 + current_date.getSeconds();
    
    var ratings_obj = new Object;
    var tier_label = collect_label();
    var set_name = collect_set_name();

    ratings_obj.meta = {"collection_date": datetime, "label": tier_label, "set": set_name, "version": 2.0};
    ratings_obj.ratings = {}
    
    for (var i = 0; i < color_ids.length; i++)
    {
        ratings_obj = collect_column_ratings(color_ids[i], ratings_obj);
    }
        
    RatingsExport (ratings_obj);
}

function collect_column_ratings (columnId, ratings_obj){

    var column_string = column_prefix + columnId;
	var table_rows = document.getElementsByClassName(column_string);
    
    for(let i = 0; i < table_rows.length; i++)
    {
        let row_rating = ratings_dict[table_rows[i].getAttribute("style")];
        
        //Iterate through the columns and check for an items
        let table_items = table_rows[i].getElementsByClassName("tier_card_name");
        
        //Iterate through the items in this column
        for(let j = 0; j < table_items.length; j++)
        {
            let card_name = table_items[j].innerHTML;
            ratings_obj.ratings[card_name] = row_rating;
        }
    }
    
    
    return ratings_obj;
}

function collect_set_name (){
    var set_name = "";
    
    try{
        let tier_list_element = document.getElementById("sortable_card_tiers_app");
        
        set_name = tier_list_element.dataset.expansion;
    
    }catch(error){
        console.log(error);
    }
    
    return set_name;
}

function collect_label (){
    var tier_label = "";
    
    try{
        tier_label = document.querySelector("h2").textContent;
        
        //Check if a label was entered
        custom_label = document.getElementById("tier_label_box").value
        
        if(custom_label.length)
        {
            tier_label = custom_label;
        }
        
    }catch(error){
        console.log(error);
    }
    
    return tier_label;
}
function RatingsExport (ratings_obj){

	var url = document.URL.split("/");

    var filename = `Tier_${ratings_obj.meta.set}_${Date.now().toString()}.txt`
	
	var _ratingObj = JSON.stringify(ratings_obj , null, 4); //indentation in json format, human readable
	
	var vLink = document.createElement('a'),
	vBlob = new Blob([_ratingObj], {type: "octet/stream"}),
	vName = filename;
	vUrl = window.URL.createObjectURL(vBlob);
	vLink.setAttribute('href', vUrl);
	vLink.setAttribute('download', vName );
	vLink.click();
}

