let uploadedFiles = []; 

$(document).ready(function(){

    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })

    $("#dropArea").click(function () {
        $("#imagesUpload").click();
    });

    $("#btnSaveProduct").click(function () {
        $("#frmNpr").submit();
    })

    $("#btnCancelProduct").click(function () {
       alert("Cancelado");
    })
    
    $("#imagesUpload").change(function (event) {
        let files = Array.from(event.target.files); 
        if (uploadedFiles.length + files.length > 10) {
            alert("Solo puedes subir hasta 10 imágenes.");
            $("#imagesUpload").val('');
            return;
        }
        $('#dropArea').hide();
        $('#divPreviewContenedor').css("display", "flex");
        if(uploadedFiles.length==0){
            var firstImage = uploadedFiles.length === 0 ? "TRUE" : "FALSE";
        }else{
            var firstImage = "FALSE";
        }
        
        files.forEach(file => {
            if (!uploadedFiles.some(f => f.name === file.name && f.size === file.size)) {
                uploadedFiles.push(file);
                let reader = new FileReader();
                let index = uploadedFiles.findIndex(f => f.name === file.name && f.size === file.size);
                reader.onload = function (e) {
                    let img = $("<img>")
                        .attr("src", e.target.result)
                        .attr("data-portada", firstImage)
                        .attr("data-index", file.name)
                        .addClass("preview-img")
                        .click(function () {
                            $('#previewArea').html("<img src='" + $(this).attr('src') + "'>");
                            let getPortada = $(this).attr('data-portada');
                            if (getPortada == 'TRUE') {
                                $('#previewAreaOptions').html("<i onclick=deleteImagen('TRUE','"+file.name+"') class='menu-icon size22 mdi mdi-trash-can-outline'></i><br/><span onclick=setMarcaPortada('TRUE','"+file.name+"') class='mdi colorBlueSel size22 mdi-star-box'></span>");
                                $("#previewArea").removeClass("hide-before");
                            } else {
                                $('#previewAreaOptions').html("<i onclick=deleteImagen('FALSE','"+file.name+"') class='menu-icon size22 mdi mdi-trash-can-outline'></i><br/><span  onclick=setMarcaPortada('FALSE','"+file.name+"') class='mdi colorGray size22 mdi-star-box'></span>");
                                $("#previewArea").addClass("hide-before");
                            }
                        });
                    $("#previewContainer").append(img);    
                    if (firstImage == "TRUE") { 
                        $('#previewArea').html("<img src='" + e.target.result + "'>");
                        $('#previewAreaOptions').html("<i onclick=deleteImagen('TRUE','"+file.name+"') class='menu-icon size22 mdi mdi-trash-can-outline'></i><br/><span onclick=setMarcaPortada('TRUE','"+file.name+"') class='mdi colorBlueSel size22 mdi-star-box'></span>");
                        $("#previewArea").removeClass("hide-before");
                        firstImage = "FALSE"; 
                    }
                };
                reader.readAsDataURL(file);
            }
        });
        $(".preview-img-add").remove(); 
        let imgAdd = $("<img>")
            .attr("src", "images/btnAddImagen.png")
            .attr("data-portada", firstImage)
            .addClass("preview-img-add")
            .click(function () {
                $("#imagesUpload").click();
            });        
        $("#previewContainer").prepend(imgAdd);
    });

    $("#dimensiones").inputmask({
        mask: "9{1,5}  x  9{1,5}  x  9{1,5}",
        greedy: false,
        placeholder: " "
    });
    
    $("#swFabricantes").change(function () {
        if ($(this).is(":checked")) {
           $("#fabricanteDiv").hide();
        }else{
            $("#fabricanteDiv").show();
        }
    });


    $("#frmNpr").on("submit", function (event) {
        event.preventDefault();
        let formData = new FormData(this);

        uploadedFiles.forEach((file, index) => {
            formData.append("imagenes[]", file);
            let isPortada = $("img[data-index='" + file.name + "']").attr("data-portada") === "TRUE" ? 1 : 0;
            formData.append("portadas[]", isPortada);
        });

        $.ajax({
            url: "includes/productos/_saveProducto.php",
            type: "POST",
            data: formData,
            contentType: false,
            processData: false,
            dataType: "json",
            success: function (response) {
                if (response.success) {
                    Swal.fire({
                        title: "Producto creado satisfactoriamente!",
                        icon: "success",
                        draggable: false
                    }).then((result) => {
                        location.reload();
                    })
                } else {
                    Swal.fire({
                        icon: "error",
                        title: "Oops...",
                        text: "Hubo un error al procesar su solicitud! "+response.message,
                        footer: '<a class="reporrError">Reportar este error</a>'
                    });
                }
            },
            error: function () {
                Swal.fire({
                    icon: "error",
                    title: "Oops...",
                    text: "Hubo un error al procesar su solicitud! ",
                    footer: '<a class="reporrError">Reportar este error</a>'
                });
            }
        });
    });

    $(".select2").select2({
        theme: 'bootstrap',
        width: '100%',
        templateResult: function(state) {
            if (!state.id) return state.text;
            if (state.element.value === "especial") {
                return $('<div class="optionLink"><div style="float:left"><i style="font-size:16px" class="menu-icon mdi mdi-settings"></i></div><div style="float:left; padding:3px 0px 0px 4px">' + state.text + '</div><div style="clear:both"></div></div>');
            }
            return state.text;
        },
        templateSelection: function(state) {
            return state.text;
        }
    });

    $("#unidad").on("select2:select", function(e) {
        if (e.params.data.id === "especial") {
            alert("asd");
            return false;
        }
    });
});

function deleteImagen(filename) {
    let index = uploadedFiles.findIndex(file => file.name === filename);
    if (index !== -1) {
        uploadedFiles.splice(index, 1);
    }
    var getPortada = $("img[data-index='"+filename+"']").attr("data-portada");
    $("img[data-index='"+filename+"']").remove();
    if (uploadedFiles.length === 0) {
        $("#dropArea").show();
        $('#divPreviewContenedor').css("display", "none");
    }else{
        let setfilename = uploadedFiles[0].name;
        $("img[data-portada='TRUE']").attr("data-portada", "FALSE");
        $("img[data-index='" + setfilename + "']").attr("data-portada","TRUE");
        $("img[data-index='" + setfilename + "']").trigger("click");
    }
}

function setMarcaPortada(portada,filename){
    if (portada === 'FALSE') {
        let index = uploadedFiles.findIndex(file => file.name === filename);
        if (index !== -1) {  
            // Primero, establecer todas las imágenes a data-portada="FALSE"
            $("img[data-portada='TRUE']").attr("data-portada", "FALSE");

            // Luego, asignar TRUE a la imagen seleccionada
            $("img[data-index='" + filename + "']").attr("data-portada", "TRUE");
            $("img[data-index='" + filename + "']").trigger("click");
        }
    }
}

function openPreviewImg(){
    $(this).css("display", "none");
}