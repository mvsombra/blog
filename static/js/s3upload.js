(function() {
    document.getElementById("img").onchange = function(){
        var files = document.getElementById("img").files;
        var file = files[0];
        if(!file){
            return alert("No file selected.");
        }
        getSignedRequest(file);
    };
})();

function getSignedRequest(file){
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/sign_s3?file_name="+file.name+"&file_type="+file.type);
    xhr.onreadystatechange = function(){
        if(xhr.readyState === 4){
            if(xhr.status === 200){
                var response = JSON.parse(xhr.responseText);
                uploadFile(file, response.data, response.url);
            }
            else{
                alert("Não foi possível conectar");
            }
        }
    };
    xhr.send();
}

function uploadFile(file, s3Data, url){
    var xhr = new XMLHttpRequest();
    xhr.open("POST", s3Data.url);

    var postData = new FormData();
    for(key in s3Data.fields){
        postData.append(key, s3Data.fields[key]);
    }
    postData.append('file', file);

    xhr.onreadystatechange = function() {
        if(xhr.readyState === 4){
            if(xhr.status === 200 || xhr.status === 204){
                alert("sucesso");
            }
            else{
                alert("Não foi possível realizar o upload.");
            }
        }
    };
    xhr.send(postData);
}