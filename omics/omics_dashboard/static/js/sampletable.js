$(document).ready(function() {
    $('#samples').DataTable( {
        dom: 'Bfrtip',
        select: true,
        buttons: [
            {
                text: 'Select Filtered',
                action: function(e, dt, node, config){
                    this.rows({search: 'applied'}).select();
                }
            },
            {
                text: 'Deselect All',
                extend: 'selectNone'
            },
            {
                text: 'Create Collection <i class="fas fa-angle-double-right"></i>',
                action: function(e, dt, node, config){
                    var row_ids = this.rows({selected: true}).ids().map(function (x){return x.split('-')[1]});
                    if (row_ids.length > 0) {
                        window.location.replace('/omics/collections/create?sampleIds="' + row_ids.join() + '"');
                    }
                },
                className: 'btn-success'
            }
        ],
        "scrollX": true,
        initComplete: function () {
            this.api().columns().every( function () {
                var column = this;
                var select = $('<select><option value=""></option></select>')
                    .appendTo( $(column.footer()).empty() )
                    .on( 'change', function () {
                        var val = $.fn.dataTable.util.escapeRegex(
                            $(this).val()
                        );

                        column
                            .search( val ? '^'+val+'$' : '', true, false )
                            .draw();
                    } );

                column.data().unique().sort().each( function ( d, j ) {
                    var text = d.replace(/<(?:.|\n)*?>/gm, '');
                    select.append( '<option value="' + text +'">' + text + '</option>' )
                } );
            } );
        }
    } );
    //kluges to handle styling from dataTables
    $('.dt-buttons').removeClass('btn-group');
    $('.btn-success').removeClass('btn-secondary');
    $('.sampletd').blur(function() {
        //var info = this.attr('id').split(',');
        //hard coding the url is bad, but necessary
        //perhaps the frontend and backend can be fully separated later?
        var id_attr = $(this).attr('id').split(',');
        var id = id_attr[0];
        var body = {};
        body[id_attr[1]] = $(this).text();
        var url = '/omics/api/samples/' + id;
        $.ajax({
            type: "POST",
            data: JSON.stringify(body),
            url: url,
            contentType: "application/json"
        }).done(function(res){
            var key = Object.keys(body);
            var message = 'Changed ' + key + ' to ' + body[key];
            console.log(res);
            console.log(url);
            $('#failModalLabel').text('Entry Updated');
            $('#failModalBody').text(message);
            $('#failModal').modal();
        }).fail(function(res){
            $('#failModalLabel').text('Update Failed');
            console.log(url);
            console.log(res);
            $('#failModalBody').text(res.responseJSON.message);
            $('#failModal').modal();
        });
    });
} );
