<!-- Adapted from DevenW/ManuChain_vue at 8b37e5f; original panel layout retained. See PROVENANCE.md. -->
<template>
    <el-row class="panel-group" justify=center align=middle>
        <div class="top-panel-area">
            <el-col :span="12" :offset="1" class="card-panel-col">
                <div class="card-panel">
                    <div class="card-panel-icon-wrapper icon-people">
                        <svg-icon icon-class="chart" class-name="card-panel-icon"/>
                    </div>
                    <div class="card-panel-description">
                        <div class="card-panel-text">
                            Evaluated records
                        </div>
                        <count-to :start-val="0" :end-val='latestNumber' :duration="2600" class="card-panel-num"/>
                    </div>
                </div>
            </el-col>

            <el-col :span="12" class="card-panel-col">
                <div class="card-panel">
                    <div class="card-panel-icon-wrapper icon-message">
                        <svg-icon icon-class="message" class-name="card-panel-icon"/>
                    </div>
                    <div class="card-panel-description">
                        <div class="card-panel-text">
                            Predicted risk
                        </div>
                        <count-to :start-val="0" :end-val="txn" :duration="3000" class="card-panel-num"/>
                    </div>
                </div>
            </el-col>
        </div>

        <div class="top-panel-area">
            <el-col class="card-panel-col">
                <div class="card-panel">
                    <div class="card-panel-icon-wrapper icon-money">
                        <svg-icon icon-class="money" class-name="card-panel-icon"/>
                    </div>
                    <div class="card-panel-description">
                        <div class="card-panel-text">
                            Outer folds
                        </div>
                        <count-to :start-val="0" :end-val="pendingTxn" :duration="3200" class="card-panel-num"/>
                    </div>
                </div>
            </el-col>

            <el-col class="card-panel-col">
                <div class="card-panel">
                    <div class="card-panel-icon-wrapper icon-shopping">
                        <svg-icon icon-class="peoples" class-name="card-panel-icon"/>
                    </div>
                    <div class="card-panel-description">
                        <div class="card-panel-text">
                            Base learners
                        </div>
                        <count-to :start-val="0" :end-val="pbftView" :duration="3600" class="card-panel-num"/>
                    </div>
                </div>
            </el-col>
        </div>
    </el-row>
</template>

<script>
    import CountTo from 'vue-count-to'



    export default {
      components: {CountTo},
      props: {summary: {type: Object, required: true}},
      computed: {
        latestNumber() {return this.summary.records},
        txn() {return this.summary.risk},
        pendingTxn() {return this.summary.folds},
        pbftView() {return this.summary.models}
      }
    }

</script>


<style lang="scss" scoped>
    .panel-group {
        height: 100%;
        width: 100%;
        position: relative;
        vertical-align: middle;
        margin: 0 auto;

        .top-panel-area {
            position: relative;
            width: 100%;
            height: 50%;
            margin: 0 auto;
        }

        .card-panel-col {
            width: 50%;
            height: 100%;
            margin: 0 auto;
            vertical-align: middle;
            position: relative;
        }


        .card-panel {
            width: 80%;
            height: 60%;
            cursor: pointer;
            font-size: 12px;
            position: absolute;
            overflow: hidden;
            color: #666;
            background: #fff;
            border-radius: 15px;
            box-shadow: 4px 4px 40px rgba(0, 0, 0, .05);
            border-color: rgba(0, 0, 0, .05);
            top: 0;
            right: 0;
            bottom: 0;
            left: 0;
            margin: auto;


            &:hover {
                .card-panel-icon-wrapper {
                    color: #fff;
                }

                .icon-people {
                    background: #40c9c6;
                }

                .icon-message {
                    background: #36a3f7;
                }

                .icon-money {
                    background: #f4516c;
                }

                .icon-shopping {
                    background: #34bfa3
                }
            }

            .icon-people {
                color: #40c9c6;
            }

            .icon-message {
                color: #36a3f7;
            }

            .icon-money {
                color: #f4516c;
            }

            .icon-shopping {
                color: #34bfa3
            }

            .card-panel-icon-wrapper {
                float: left;
                margin: 14px 0 0 14px;
                padding: 16px;
                transition: all 0.38s ease-out;
                border-radius: 6px;
            }

            .card-panel-icon {
                float: left;
                font-size: 48px;
            }

            .card-panel-description {
                float: right;
                font-weight: bold;
                margin: 26px;
                margin-left: 0px;

                .card-panel-text {
                    line-height: 18px;
                    color: rgba(0, 0, 0, 0.45);
                    font-size: 16px;
                    margin-bottom: 12px;
                }

                .card-panel-num {
                    font-size: 20px;
                }
            }
        }
    }

    @media (max-width: 550px) {
        .card-panel-description {
            display: none;
        }

        .card-panel-icon-wrapper {
            float: none !important;
            width: 100%;
            height: 100%;
            margin: 0 !important;

            .svg-icon {
                display: block;
                margin: 14px auto !important;
                float: none !important;
            }
        }
    }
</style>
